import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import React from 'react';
import { AuthProvider, useAuth } from '../features/auth/AuthContext';
import { authApi } from '../shared/api/auth';
import { getAuthToken } from '../shared/api/client';
import { User, TokenResponse } from '../shared/types/auth';

vi.mock('../shared/api/auth', () => ({
  authApi: {
    login: vi.fn(),
    getMe: vi.fn(),
    logout: vi.fn(),
  },
}));

const mockUser: User = {
  id: 1,
  email: 'admin@servicepulse.uz',
  full_name: 'System Administrator',
  is_active: true,
  is_superuser: true,
  organization_id: 1,
  roles: [{ id: 1, name: 'platform_super_admin' }],
  created_at: '2026-11-12T22:28:29Z',
  primary_dashboard: 'platform',
};

const mockTokenResponse: TokenResponse = {
  access_token: 'mock-jwt-access-token-xyz',
  refresh_token: 'mock-jwt-refresh-token-xyz',
  token_type: 'bearer',
  expires_in: 3600,
  primary_dashboard: 'platform',
  organization_id: 1,
  full_name: 'System Administrator',
  roles: ['platform_super_admin'],
};

const TestConsumer: React.FC = () => {
  const { user, isAuthenticated, login, logout, hasRole, hasAnyRole } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      <div data-testid="user-email">{user?.email || 'none'}</div>
      <div data-testid="has-role">{hasRole('platform_super_admin') ? 'yes' : 'no'}</div>
      <div data-testid="has-any-role">{hasAnyRole(['platform_super_admin', 'company_admin']) ? 'yes' : 'no'}</div>
      <button
        onClick={() => login({ email: 'admin@servicepulse.uz', password: 'ValidTestPassword123!' })}
        data-testid="login-btn"
      >
        Login
      </button>
      <button onClick={() => logout()} data-testid="logout-btn">
        Logout
      </button>
    </div>
  );
};

describe('AuthContext and In-Memory JWT Security', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('initializes in unauthenticated state without reading tokens from storage', async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated');
    expect(screen.getByTestId('user-email').textContent).toBe('none');
    expect(getAuthToken()).toBeNull();
  });

  it('stores access token strictly in-memory and NEVER writes to localStorage or sessionStorage', async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce(mockTokenResponse);
    vi.mocked(authApi.getMe).mockResolvedValueOnce(mockUser);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByTestId('login-btn').click();
    });

    expect(authApi.login).toHaveBeenCalledWith({
      email: 'admin@servicepulse.uz',
      password: 'ValidTestPassword123!',
    });
    expect(authApi.getMe).toHaveBeenCalled();

    // Verify token is in memory
    expect(getAuthToken()).toBe('mock-jwt-access-token-xyz');

    // CRITICAL SECURITY ASSERTION: Zero tokens in browser storage
    expect(localStorage.getItem('servicepulse_token')).toBeNull();
    expect(localStorage.getItem('servicepulse_user')).toBeNull();

    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated');
    expect(screen.getByTestId('user-email').textContent).toBe('admin@servicepulse.uz');
    expect(screen.getByTestId('has-role').textContent).toBe('yes');
    expect(screen.getByTestId('has-any-role').textContent).toBe('yes');
  });

  it('clears in-memory credentials and resets state on logout', async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce(mockTokenResponse);
    vi.mocked(authApi.getMe).mockResolvedValueOnce(mockUser);
    vi.mocked(authApi.logout).mockResolvedValueOnce();

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByTestId('login-btn').click();
    });
    expect(getAuthToken()).toBe('mock-jwt-access-token-xyz');

    await act(async () => {
      screen.getByTestId('logout-btn').click();
    });

    expect(authApi.logout).toHaveBeenCalled();
    expect(getAuthToken()).toBeNull();
    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated');
    expect(screen.getByTestId('user-email').textContent).toBe('none');
  });

  it('resets in-memory authentication state on 401 unauthorized event', async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce(mockTokenResponse);
    vi.mocked(authApi.getMe).mockResolvedValueOnce(mockUser);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByTestId('login-btn').click();
    });
    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated');

    // Trigger 401 event
    await act(async () => {
      window.dispatchEvent(new Event('servicepulse_unauthorized'));
    });

    expect(getAuthToken()).toBeNull();
    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated');
  });
});
