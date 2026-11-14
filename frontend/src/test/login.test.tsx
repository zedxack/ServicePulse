import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from '../features/auth/LoginPage';
import * as AuthContextModule from '../features/auth/AuthContext';
import '../i18n/config';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('LoginPage Component & Production Security', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form with email and password inputs and submit button', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      login: vi.fn(),
      joinOrganization: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(false),
      hasAnyRole: vi.fn().mockReturnValue(false),
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByPlaceholderText('nom@servicepulse.uz')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••••••')).toBeInTheDocument();
    expect(screen.getByTestId('login-submit-btn')).toBeInTheDocument();
  });

  it('does NOT render demo account selectors when import.meta.env.DEV is false', () => {
    const originalDev = import.meta.env.DEV;
    try {
      // Simulate production environment
      (import.meta.env as unknown as { DEV: boolean }).DEV = false;

      vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
        user: null,
        token: null,
        isLoading: false,
        isAuthenticated: false,
        login: vi.fn(),
        joinOrganization: vi.fn(),
        logout: vi.fn(),
        hasRole: vi.fn().mockReturnValue(false),
        hasAnyRole: vi.fn().mockReturnValue(false),
      });

      render(
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      );

      // Verify that no dev demo accounts element or demo labels are rendered in production mode
      expect(screen.queryByTestId('dev-demo-accounts')).not.toBeInTheDocument();
      expect(screen.queryByText('DEV ONLY')).not.toBeInTheDocument();
      expect(screen.queryByText(/Quick Demo Accounts/i)).not.toBeInTheDocument();
    } finally {
      (import.meta.env as unknown as { DEV: boolean }).DEV = originalDev;
    }
  });

  it('handles successful user login and navigates to primary dashboard', async () => {
    const mockLogin = vi.fn().mockResolvedValue({
      id: 1,
      email: 'admin@servicepulse.uz',
      full_name: 'System Administrator',
      primary_dashboard: 'platform',
      roles: [{ id: 1, name: 'platform_super_admin' }],
    });

    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      login: mockLogin,
      joinOrganization: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(true),
      hasAnyRole: vi.fn().mockReturnValue(true),
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('nom@servicepulse.uz'), {
      target: { value: 'admin@servicepulse.uz' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••••••'), {
      target: { value: 'SecretPassword123!' },
    });

    fireEvent.click(screen.getByTestId('login-submit-btn'));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'admin@servicepulse.uz',
        password: 'SecretPassword123!',
      });
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard/platform', { replace: true });
    });
  });

  it('displays error alert on invalid credentials without exposing sensitive details', async () => {
    const mockLogin = vi.fn().mockRejectedValue({
      response: {
        status: 401,
        data: { detail: 'Incorrect email or password' },
      },
    });

    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      login: mockLogin,
      joinOrganization: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(false),
      hasAnyRole: vi.fn().mockReturnValue(false),
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('nom@servicepulse.uz'), {
      target: { value: 'wrong@servicepulse.uz' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••••••'), {
      target: { value: 'WrongPass!' },
    });

    fireEvent.click(screen.getByTestId('login-submit-btn'));

    await waitFor(() => {
      expect(screen.getByText('Incorrect email or password')).toBeInTheDocument();
    });
  });
});
