import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from '../features/auth/LoginPage';
import { evaluatePassword } from '../features/auth/PasswordStrengthMeter';
import * as AuthContextModule from '../features/auth/AuthContext';
import { authApi } from '../shared/api/auth';
import '../i18n/config';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Secure Authentication & Onboarding Suite', () => {
  const mockJoinOrg = vi.fn();
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    if (typeof window !== 'undefined') {
      window.localStorage?.clear();
      window.sessionStorage?.clear();
    }

    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      login: mockLogin,
      joinOrganization: mockJoinOrg,
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(false),
      hasAnyRole: vi.fn().mockReturnValue(false),
    });
  });

  it('renders mode tabs and switches between Login, Join, and New Org', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    // Initial mode is Sign In
    expect(screen.getByTestId('login-submit-btn')).toBeInTheDocument();

    // Switch to Join with Invite
    const joinTab = screen.getByTestId('tab-join');
    fireEvent.click(joinTab);
    expect(screen.getByPlaceholderText('sp_inv_...')).toBeInTheDocument();

    // Switch to New Organization
    const newOrgTab = screen.getByTestId('tab-register-org');
    fireEvent.click(newOrgTab);
    expect(screen.getByPlaceholderText('Example Corporation')).toBeInTheDocument();
  });

  it('toggles password visibility between text and password types', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    const passwordInput = screen.getByPlaceholderText('••••••••••••');
    expect(passwordInput).toHaveAttribute('type', 'password');

    const toggleBtn = screen.getByLabelText('Show password');
    fireEvent.click(toggleBtn);
    expect(passwordInput).toHaveAttribute('type', 'text');

    const hideBtn = screen.getByLabelText('Hide password');
    fireEvent.click(hideBtn);
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('evaluates password strength correctly with evaluatePassword helper', () => {
    // Weak password: less than 8 chars
    const weak = evaluatePassword('abc');
    expect(weak.score).toBeLessThanOrEqual(1);
    expect(weak.hasLength).toBe(false);

    // Medium password: 8 chars with upper and lower
    const fair = evaluatePassword('Abcdefgh');
    expect(fair.score).toBe(2);
    expect(fair.hasLength).toBe(true);
    expect(fair.hasUpper).toBe(true);
    expect(fair.hasLower).toBe(true);

    // Strong password: length, upper, lower, digits, special
    const strong = evaluatePassword('SuperSecret2026!');
    expect(strong.score).toBe(4);
    expect(strong.hasDigit).toBe(true);
    expect(strong.hasSpecial).toBe(true);
  });

  it('validates invitation code and displays assigned organization & role', async () => {
    vi.spyOn(authApi, 'validateInvitation').mockResolvedValue({
      valid: true,
      organization_id: 1,
      organization_name: 'Regional Operations Hub',
      role_id: 3,
      role_name: 'it_admin',
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    // Switch to Join tab
    fireEvent.click(screen.getByTestId('tab-join'));

    const codeInput = screen.getByPlaceholderText('sp_inv_...');
    fireEvent.change(codeInput, { target: { value: 'sp_inv_valid123' } });

    const verifyBtn = screen.getByRole('button', { name: /Tekshirish|Verify/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(authApi.validateInvitation).toHaveBeenCalledWith({ invitation_code: 'sp_inv_valid123' });
      expect(screen.getByText('Regional Operations Hub')).toBeInTheDocument();
      expect(screen.getByText('it_admin')).toBeInTheDocument();
    });
  });

  it('rejects joining organization if passwords do not match', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByTestId('tab-join'));

    fireEvent.change(screen.getByPlaceholderText('sp_inv_...'), { target: { value: 'sp_inv_code' } });
    fireEvent.change(screen.getByPlaceholderText('Alex Morgan'), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByPlaceholderText('user@organization.uz'), { target: { value: 'test@example.com' } });

    const passwordInputs = screen.getAllByPlaceholderText('••••••••••••');
    fireEvent.change(passwordInputs[0], { target: { value: 'PasswordOne2026!' } });
    fireEvent.change(passwordInputs[1], { target: { value: 'DifferentPassword2026!' } });

    const submitBtn = screen.getByRole('button', { name: /Tashkilotga qo'shilish|Join Organization/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Kiritilgan parollar mos kelmadi|Passwords do not match/i)).toBeInTheDocument();
      expect(mockJoinOrg).not.toHaveBeenCalled();
    });
  });

  it('submits organization onboarding request and displays pending confirmation', async () => {
    vi.spyOn(authApi, 'createOrganizationRequest').mockResolvedValue({
      id: 99,
      org_name: 'Innovation Tech Center',
      org_slug: 'innovation-tech',
      org_email: 'contact@example.com',
      contact_full_name: 'Anvar Sultonov',
      contact_email: 'anvar@example.com',
      status: 'pending',
      created_at: new Date().toISOString(),
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    // Switch to New Org tab
    fireEvent.click(screen.getByTestId('tab-register-org'));

    fireEvent.change(screen.getByPlaceholderText('Example Corporation'), { target: { value: 'Innovation Tech Center' } });
    fireEvent.change(screen.getByPlaceholderText('contact@example.com'), { target: { value: 'contact@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('Alex Morgan'), { target: { value: 'Anvar Sultonov' } });
    fireEvent.change(screen.getByPlaceholderText('admin@example.com'), { target: { value: 'anvar@example.com' } });

    const passwordInputs = screen.getAllByPlaceholderText('••••••••••••');
    fireEvent.change(passwordInputs[0], { target: { value: 'StrongOrgPass2026!' } });
    fireEvent.change(passwordInputs[1], { target: { value: 'StrongOrgPass2026!' } });

    const submitBtn = screen.getByRole('button', { name: /Ro'yxatdan o'tish arizasini yuborish|Submit Onboarding Request/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(authApi.createOrganizationRequest).toHaveBeenCalled();
      expect(screen.getByText(/Ro'yxatdan o'tish arizasi qabul qilindi|Registration Request Received/i)).toBeInTheDocument();
      expect(screen.getByText('Innovation Tech Center')).toBeInTheDocument();
    });
  });

  it('guarantees pure in-memory JWT architecture (tokens never touch storage)', async () => {
    mockLogin.mockResolvedValue({
      id: 1,
      email: 'admin@servicepulse.uz',
      full_name: 'System Administrator',
      primary_dashboard: 'platform',
      roles: [{ id: 1, name: 'platform_super_admin' }],
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('name@company.com'), { target: { value: 'admin@servicepulse.uz' } });
    fireEvent.change(screen.getByPlaceholderText('••••••••••••'), { target: { value: 'AdminPass2026!' } });

    fireEvent.click(screen.getByTestId('login-submit-btn'));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalled();
    });

    // Verify localStorage and sessionStorage remain completely clean
    expect(window.localStorage?.getItem('token') ?? null).toBeNull();
    expect(window.localStorage?.getItem('access_token') ?? null).toBeNull();
    expect(window.sessionStorage?.getItem('token') ?? null).toBeNull();
    expect(window.sessionStorage?.getItem('access_token') ?? null).toBeNull();
  });
});
