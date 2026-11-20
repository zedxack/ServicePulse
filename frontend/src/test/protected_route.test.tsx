import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from '../features/auth/ProtectedRoute';
import * as AuthContextModule from '../features/auth/AuthContext';
import { User } from '../shared/types/auth';

describe('ProtectedRoute Component and RBAC Authorization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const employeeUser: User = {
    id: 5,
    email: 'employee@servicepulse.uz',
    full_name: 'Muhammadyusuf Usmonov',
    is_active: true,
    is_superuser: false,
    organization_id: 1,
    roles: [{ id: 5, name: 'employee' }],
    created_at: '2026-11-12T22:28:29Z',
    primary_dashboard: 'employee',
  };

  const sysadminUser: User = {
    id: 2,
    email: 'support@servicepulse.uz',
    full_name: 'Support Engineer',
    is_active: true,
    is_superuser: false,
    organization_id: 1,
    roles: [{ id: 3, name: 'it_admin' }],
    created_at: '2026-11-12T22:28:29Z',
    primary_dashboard: 'sysadmin',
  };

  it('redirects unauthenticated visitor to /login', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      login: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(false),
      hasAnyRole: vi.fn().mockReturnValue(false),
    });

    render(
      <MemoryRouter initialEntries={['/dashboard/sysadmin']}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/dashboard/sysadmin"
            element={
              <ProtectedRoute allowedRoles={['it_admin']}>
                <div>Secret SysAdmin Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Secret SysAdmin Dashboard')).not.toBeInTheDocument();
  });

  it('redirects authenticated employee without it_admin role to /unauthorized', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: employeeUser,
      token: 'valid-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(false),
      hasAnyRole: vi.fn().mockReturnValue(false),
    });

    render(
      <MemoryRouter initialEntries={['/dashboard/sysadmin']}>
        <Routes>
          <Route path="/unauthorized" element={<div>Unauthorized Access Denied</div>} />
          <Route
            path="/dashboard/sysadmin"
            element={
              <ProtectedRoute allowedRoles={['it_admin']}>
                <div>Secret SysAdmin Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Unauthorized Access Denied')).toBeInTheDocument();
    expect(screen.queryByText('Secret SysAdmin Dashboard')).not.toBeInTheDocument();
  });

  it('allows access to sysadmin dashboard for authorized user', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: sysadminUser,
      token: 'valid-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockImplementation((r) => r === 'it_admin'),
      hasAnyRole: vi.fn().mockImplementation((roles: string[]) => roles.includes('it_admin')),
    });

    render(
      <MemoryRouter initialEntries={['/dashboard/sysadmin']}>
        <Routes>
          <Route path="/unauthorized" element={<div>Unauthorized Access Denied</div>} />
          <Route
            path="/dashboard/sysadmin"
            element={
              <ProtectedRoute allowedRoles={['it_admin']}>
                <div>Secret SysAdmin Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Secret SysAdmin Dashboard')).toBeInTheDocument();
  });

  it('preserves authenticated session state when 403 forbidden is encountered', () => {
    const mockLogout = vi.fn();
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: employeeUser,
      token: 'valid-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: mockLogout,
      hasRole: vi.fn().mockReturnValue(false),
      hasAnyRole: vi.fn().mockReturnValue(false),
    });

    render(
      <MemoryRouter initialEntries={['/dashboard/platform']}>
        <Routes>
          <Route path="/unauthorized" element={<div>Unauthorized Access Denied - User Still Active</div>} />
          <Route
            path="/dashboard/platform"
            element={
              <ProtectedRoute allowedRoles={['platform_super_admin']}>
                <div>Platform Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Unauthorized Access Denied - User Still Active')).toBeInTheDocument();
    // Verify 403 authorization denial does NOT trigger logout
    expect(mockLogout).not.toHaveBeenCalled();
  });
});
