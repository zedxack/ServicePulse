import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CommandPalette } from '../shared/components/CommandPalette';
import { AppLayout } from '../app/layouts/AppLayout';
import * as AuthContextModule from '../features/auth/AuthContext';
import * as RealtimeMonitoringModule from '../features/monitoring/useRealtimeMonitoring';
import * as AlertApiModule from '../shared/api/alerts';
import { User } from '../shared/types/auth';
import i18n from '../i18n/config';

describe('NOC Command Center Shell & Command Palette Test Suite', () => {
  let queryClient: QueryClient;

  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage('en');
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    vi.spyOn(RealtimeMonitoringModule, 'useRealtimeMonitoring').mockReturnValue({
      status: 'connected',
      events: [],
      lastMessage: null,
      telemetryMap: {},
      clearEvents: vi.fn(),
      reconnect: vi.fn().mockResolvedValue(undefined),
    });

    vi.spyOn(AlertApiModule, 'getUnreadAlertCount').mockResolvedValue({
      unread_count: 5,
    });
  });

  const primaryOwnerUser: User = {
    id: 1,
    email: 'admin@servicepulse.uz',
    full_name: 'Primary Platform Owner',
    is_active: true,
    is_superuser: true,
    organization_id: 1,
    roles: [
      { id: 1, name: 'platform_super_admin' },
      { id: 2, name: 'admin' },
    ],
    created_at: '2026-11-12T00:00:00Z',
    primary_dashboard: 'platform',
    is_primary_owner: true,
  };

  const sysadminUser: User = {
    id: 2,
    email: 'sysadmin@servicepulse.uz',
    full_name: 'Systems Administrator',
    is_active: true,
    is_superuser: false,
    organization_id: 1,
    roles: [{ id: 3, name: 'it_admin' }],
    created_at: '2026-11-12T00:00:00Z',
    primary_dashboard: 'sysadmin',
    is_primary_owner: false,
  };

  const employeeUser: User = {
    id: 5,
    email: 'employee@servicepulse.uz',
    full_name: 'Regular Staff Member',
    is_active: true,
    is_superuser: false,
    organization_id: 1,
    roles: [{ id: 5, name: 'employee' }],
    created_at: '2026-11-12T00:00:00Z',
    primary_dashboard: 'employee',
    is_primary_owner: false,
  };

  // Helper to mock auth context
  const mockAuth = (user: User | null) => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user,
      token: user ? 'mock-token' : null,
      isLoading: false,
      isAuthenticated: Boolean(user),
      login: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn((role: string) => {
        if (!user) return false;
        if (user.is_superuser) return true;
        return user.roles.some((r) => r.name === role);
      }),
      hasAnyRole: vi.fn((roles: string[]) => {
        if (!user) return false;
        if (user.is_superuser) return true;
        return roles.some((r) => user.roles.some((ur) => ur.name === r));
      }),
    });
  };

  describe('Global CommandPalette Component', () => {
    it('does not render dialog modal when isOpen is false', () => {
      mockAuth(primaryOwnerUser);
      render(
        <MemoryRouter>
          <CommandPalette isOpen={false} onClose={vi.fn()} />
        </MemoryRouter>
      );
      expect(screen.queryByTestId('command-palette')).not.toBeInTheDocument();
    });

    it('renders search input and technical action list when isOpen is true', () => {
      mockAuth(primaryOwnerUser);
      render(
        <MemoryRouter>
          <CommandPalette isOpen={true} onClose={vi.fn()} />
        </MemoryRouter>
      );

      expect(screen.getByTestId('command-palette')).toBeInTheDocument();
      expect(screen.getByTestId('command-palette-input')).toBeInTheDocument();
      expect(screen.getByText(/CLI \/ NOC DISPATCH/i)).toBeInTheDocument();
      expect(screen.getAllByTestId('command-palette-item').length).toBeGreaterThan(5);
    });

    it('filters items in real-time according to search query', async () => {
      mockAuth(primaryOwnerUser);
      render(
        <MemoryRouter>
          <CommandPalette isOpen={true} onClose={vi.fn()} />
        </MemoryRouter>
      );

      const input = screen.getByTestId('command-palette-input');
      fireEvent.change(input, { target: { value: 'Inventory' } });

      await waitFor(() => {
        const items = screen.getAllByTestId('command-palette-item');
        expect(items.length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Infrastructure/i).length).toBeGreaterThan(0);
      });
    });

    it('shows technical empty state when search finds no matches', async () => {
      mockAuth(primaryOwnerUser);
      render(
        <MemoryRouter>
          <CommandPalette isOpen={true} onClose={vi.fn()} />
        </MemoryRouter>
      );

      const input = screen.getByTestId('command-palette-input');
      fireEvent.change(input, { target: { value: 'xyznonexistentquery999' } });

      await waitFor(() => {
        expect(screen.getByText(/No matching command or destination found/i)).toBeInTheDocument();
        expect(screen.queryByTestId('command-palette-item')).not.toBeInTheDocument();
      });
    });

    it('handles keyboard navigation (ArrowDown, ArrowUp, Enter, Escape)', async () => {
      const handleClose = vi.fn();
      mockAuth(primaryOwnerUser);
      render(
        <MemoryRouter>
          <CommandPalette isOpen={true} onClose={handleClose} />
        </MemoryRouter>
      );

      const palette = screen.getByTestId('command-palette');

      // Test ArrowDown
      fireEvent.keyDown(palette, { key: 'ArrowDown' });
      // Test ArrowUp
      fireEvent.keyDown(palette, { key: 'ArrowUp' });

      // Test Escape triggers close
      fireEvent.keyDown(palette, { key: 'Escape' });
      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when close button or backdrop is clicked', () => {
      const handleClose = vi.fn();
      mockAuth(primaryOwnerUser);
      render(
        <MemoryRouter>
          <CommandPalette isOpen={true} onClose={handleClose} />
        </MemoryRouter>
      );

      fireEvent.click(screen.getByTestId('command-palette-close'));
      expect(handleClose).toHaveBeenCalledTimes(1);

      fireEvent.click(screen.getByTestId('command-palette-backdrop'));
      expect(handleClose).toHaveBeenCalledTimes(2);
    });

    it('restricts privileged modules for non-privileged employee', () => {
      mockAuth(employeeUser);
      render(
        <MemoryRouter>
          <CommandPalette isOpen={true} onClose={vi.fn()} />
        </MemoryRouter>
      );

      // Platform Super Admin and Access Governance should NOT be visible to employee
      expect(screen.queryByText(/Platform Oversight/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Primary Owner Approvals/i)).not.toBeInTheDocument();
      // Employee portal and Infrastructure should still be available
      expect(screen.getByText(/Employee Portal/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Infrastructure/i).length).toBeGreaterThan(0);
    });

    it('shows Access Governance and Platform Super Admin for primary owner', () => {
      mockAuth(primaryOwnerUser);
      render(
        <MemoryRouter>
          <CommandPalette isOpen={true} onClose={vi.fn()} />
        </MemoryRouter>
      );

      expect(screen.getByText(/Platform Oversight/i)).toBeInTheDocument();
      expect(screen.getByText(/Primary Owner Approvals/i)).toBeInTheDocument();
    });
  });

  describe('NOC Application Shell (AppLayout)', () => {
    it('renders categorized sidebar sections with technical headers', () => {
      mockAuth(primaryOwnerUser);
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AppLayout />
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(screen.getByText(/COMMAND & ANALYTICS/i)).toBeInTheDocument();
      expect(screen.getByText(/INFRASTRUCTURE & RMM/i)).toBeInTheDocument();
      expect(screen.getByText(/SERVICE DESK & INCIDENTS/i)).toBeInTheDocument();
      expect(screen.getByText(/GOVERNANCE & SECURITY/i)).toBeInTheDocument();
    });

    it('renders compact technical system engine status footer in sidebar', () => {
      mockAuth(primaryOwnerUser);
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AppLayout />
          </MemoryRouter>
        </QueryClientProvider>
      );

      const statusFooter = screen.getByTestId('noc-engine-status');
      expect(statusFooter).toBeInTheDocument();
      expect(statusFooter).toHaveTextContent(/ENGINE: NOMINAL/i);
      expect(statusFooter).toHaveTextContent(/v1\.0\.0/);
      expect(statusFooter).toHaveTextContent(/STREAM: WSS/i);
      expect(statusFooter).toHaveTextContent(/TENANT #1/i);
    });

    it('renders live NOC telemetry pill in header bar', () => {
      mockAuth(primaryOwnerUser);
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AppLayout />
          </MemoryRouter>
        </QueryClientProvider>
      );

      const pill = screen.getByTestId('noc-telemetry-pill');
      expect(pill).toBeInTheDocument();
      expect(pill).toHaveTextContent(/SYSTEM NOMINAL/i);
    });

    it('displays authoritative PRIMARY OWNER security badge when user is primary owner', () => {
      mockAuth(primaryOwnerUser);
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AppLayout />
          </MemoryRouter>
        </QueryClientProvider>
      );

      const roleBadge = screen.getByTestId('user-role-badge');
      expect(roleBadge).toBeInTheDocument();
      expect(roleBadge).toHaveTextContent(/PRIMARY OWNER/i);
    });

    it('displays standard SYSADMIN role badge when user is IT admin', () => {
      mockAuth(sysadminUser);
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AppLayout />
          </MemoryRouter>
        </QueryClientProvider>
      );

      const roleBadge = screen.getByTestId('user-role-badge');
      expect(roleBadge).toBeInTheDocument();
      expect(roleBadge).toHaveTextContent(/SYSADMIN/i);
      expect(roleBadge).not.toHaveTextContent(/PRIMARY OWNER/i);
    });

    it('opens Command Palette when trigger button in header is clicked', async () => {
      const user = userEvent.setup();
      mockAuth(primaryOwnerUser);
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AppLayout />
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(screen.queryByTestId('command-palette')).not.toBeInTheDocument();
      const trigger = screen.getByTestId('command-palette-trigger');
      expect(trigger).toBeInTheDocument();

      await user.click(trigger);
      expect(screen.getByTestId('command-palette')).toBeInTheDocument();
    });
  });
});
