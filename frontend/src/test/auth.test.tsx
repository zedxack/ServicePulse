import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import React from 'react';
import { AuthProvider, useAuth } from '../features/auth/AuthContext';
import { authApi } from '../shared/api/auth';
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
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
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
        onClick={() => login({ email: 'admin@servicepulse.uz', password: 'AdminPass2026!' })}
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

describe('AuthContext and Authentication Lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('initializes in unauthenticated state when storage is empty', async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated');
    expect(screen.getByTestId('user-email').textContent).toBe('none');
  });

  it('authenticates user and loads user profile on successful login', async () => {
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
      password: 'AdminPass2026!',
    });
    expect(authApi.getMe).toHaveBeenCalled();
    expect(localStorage.getItem('servicepulse_token')).toBe('mock-access-token');
    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated');
    expect(screen.getByTestId('user-email').textContent).toBe('admin@servicepulse.uz');
    expect(screen.getByTestId('has-role').textContent).toBe('yes');
    expect(screen.getByTestId('has-any-role').textContent).toBe('yes');
  });

  it('clears credentials from storage and state on logout', async () => {
    localStorage.setItem('servicepulse_token', 'stored-token');
    localStorage.setItem('servicepulse_user', JSON.stringify(mockUser));
    vi.mocked(authApi.getMe).mockResolvedValueOnce(mockUser);
    vi.mocked(authApi.logout).mockResolvedValueOnce();

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByTestId('logout-btn').click();
    });

    expect(authApi.logout).toHaveBeenCalled();
    expect(localStorage.getItem('servicepulse_token')).toBeNull();
    expect(localStorage.getItem('servicepulse_user')).toBeNull();
    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated');
  });
});
