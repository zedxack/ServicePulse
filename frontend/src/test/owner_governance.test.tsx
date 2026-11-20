import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { OwnerAccessGovernanceSection } from '../features/dashboard/OwnerAccessGovernanceSection';
import * as AuthContextModule from '../features/auth/AuthContext';
import { authApi } from '../shared/api/auth';
import { AccessRequestRead, AccessRequestStats } from '../shared/types/auth';
import '../i18n/config';

describe('Owner Access Governance Section Test Suite', () => {
  const mockStats: AccessRequestStats = {
    pending_count: 2,
    approved_count: 5,
    rejected_count: 1,
    total_count: 8,
  };

  const mockRequests: AccessRequestRead[] = [
    {
      id: 101,
      request_type: 'it_admin_access',
      status: 'pending',
      applicant_email: 'candidate.it@example.com',
      applicant_full_name: 'Jordan IT Candidate',
      organization_id: 1,
      organization_name: 'Example Corporation',
      target_role_name: 'it_admin',
      justification: 'Needs administrative access to monitor internal servers.',
      created_at: '2026-11-15T10:00:00Z',
    },
    {
      id: 102,
      request_type: 'employee_access',
      status: 'approved',
      applicant_email: 'staff.member@example.com',
      applicant_full_name: 'Morgan Staff',
      organization_id: 1,
      organization_name: 'Example Corporation',
      target_role_name: 'employee',
      justification: 'New staff member onboarding.',
      created_at: '2026-11-15T09:00:00Z',
      reviewed_at: '2026-11-15T09:30:00Z',
      reviewed_by_id: 1,
    },
    {
      id: 103,
      request_type: 'company_admin_access',
      status: 'rejected',
      applicant_email: 'rejected.admin@example.com',
      applicant_full_name: 'Taylor Reject',
      organization_id: 2,
      organization_name: 'Second Corp',
      target_role_name: 'company_admin',
      justification: 'Requested elevated tenant admin privileges.',
      rejection_reason: 'Executive clearance not verified.',
      created_at: '2026-11-15T08:00:00Z',
      reviewed_at: '2026-11-15T08:30:00Z',
      reviewed_by_id: 1,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(authApi, 'listAccessRequests').mockResolvedValue(mockRequests);
    vi.spyOn(authApi, 'getAccessRequestStats').mockResolvedValue(mockStats);
    vi.spyOn(authApi, 'approveAccessRequest').mockResolvedValue({
      ...mockRequests[0],
      status: 'approved',
      reviewed_at: new Date().toISOString(),
      reviewed_by_id: 1,
    });
    vi.spyOn(authApi, 'rejectAccessRequest').mockResolvedValue({
      ...mockRequests[0],
      status: 'rejected',
      rejection_reason: 'Role requirements not met.',
      reviewed_at: new Date().toISOString(),
      reviewed_by_id: 1,
    });

    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 1,
        email: 'owner@example.com',
        full_name: 'Primary Owner',
        is_active: true,
        is_superuser: true,
        is_primary_owner: true,
        roles: [{ id: 1, name: 'platform_super_admin' }],
        created_at: '2026-11-15T00:00:00Z',
        primary_dashboard: 'platform',
      },
      token: 'mock-jwt-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      joinOrganization: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(true),
      hasAnyRole: vi.fn().mockReturnValue(true),
    });
  });

  it('renders governance stats cards and primary owner authority banner', async () => {
    render(
      <MemoryRouter>
        <OwnerAccessGovernanceSection />
      </MemoryRouter>
    );

    // Verify Primary Owner Authority Banner
    await waitFor(() => {
      expect(screen.getByText(/Authoritative Primary Owner Access Active/i)).toBeInTheDocument();
    });

    // Verify Stats Tabs
    expect(screen.getByRole('button', { name: /Pending \(2\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Approved \(5\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Rejected \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /All \(8\)/i })).toBeInTheDocument();
  });

  it('renders access request table and filters by search query', async () => {
    render(
      <MemoryRouter>
        <OwnerAccessGovernanceSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('candidate.it@example.com')).toBeInTheDocument();
    });

    // Search filter
    const searchInput = screen.getByPlaceholderText(/Search email, name, org/i);
    fireEvent.change(searchInput, { target: { value: 'candidate.it' } });

    expect(screen.getByText('candidate.it@example.com')).toBeInTheDocument();
    expect(screen.queryByText('staff.member@example.com')).not.toBeInTheDocument();
  });

  it('opens and closes inspection modal with accessibility attributes', async () => {
    render(
      <MemoryRouter>
        <OwnerAccessGovernanceSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('candidate.it@example.com')).toBeInTheDocument();
    });

    // Click inspect details button
    const inspectBtns = screen.getAllByTitle('Inspect Details');
    fireEvent.click(inspectBtns[0]);

    // Verify modal dialog attributes
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(within(dialog).getByText(/Access Request #101 Details/i)).toBeInTheDocument();
    expect(within(dialog).getByText('Jordan IT Candidate')).toBeInTheDocument();
    expect(within(dialog).getByText('Needs administrative access to monitor internal servers.')).toBeInTheDocument();

    // Close modal via Close text button
    const closeBtn = within(dialog).getByText('Close');
    fireEvent.click(closeBtn);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('handles authoritative approval workflow', async () => {
    render(
      <MemoryRouter>
        <OwnerAccessGovernanceSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('candidate.it@example.com')).toBeInTheDocument();
    });

    // Click approve button
    const approveBtn = screen.getByTitle('Approve Request');
    fireEvent.click(approveBtn);

    // Verify confirmation modal
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Authoritative Approval Confirmation/i)).toBeInTheDocument();

    // Click Authorize & Provision
    const confirmApproveBtn = screen.getByRole('button', { name: /Authorize & Provision/i });
    fireEvent.click(confirmApproveBtn);

    await waitFor(() => {
      expect(authApi.approveAccessRequest).toHaveBeenCalledWith(101);
      expect(screen.getByText(/Approved request for candidate.it@example.com/i)).toBeInTheDocument();
    });
  });

  it('enforces mandatory rejection reason when rejecting a request', async () => {
    render(
      <MemoryRouter>
        <OwnerAccessGovernanceSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('candidate.it@example.com')).toBeInTheDocument();
    });

    // Click reject button
    const rejectBtn = screen.getByTitle('Reject Request');
    fireEvent.click(rejectBtn);

    // Verify rejection modal
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Reject Access Request #101/i)).toBeInTheDocument();

    // Confirm button must be disabled when reason is empty or < 3 chars
    const confirmRejectBtn = screen.getByRole('button', { name: /Confirm Rejection/i });
    expect(confirmRejectBtn).toBeDisabled();

    // Enter short 2-char reason - still disabled
    const reasonTextarea = screen.getByPlaceholderText(/e\.g\., Target department quota reached/i);
    fireEvent.change(reasonTextarea, { target: { value: 'no' } });
    expect(confirmRejectBtn).toBeDisabled();

    // Enter valid rejection reason (>= 3 chars) - becomes enabled
    fireEvent.change(reasonTextarea, { target: { value: 'Role requirements not met by candidate credentials.' } });
    expect(confirmRejectBtn).not.toBeDisabled();

    fireEvent.click(confirmRejectBtn);

    await waitFor(() => {
      expect(authApi.rejectAccessRequest).toHaveBeenCalledWith(101, 'Role requirements not met by candidate credentials.');
      expect(screen.getByText(/Rejected request for candidate.it@example.com/i)).toBeInTheDocument();
    });
  });

  it('renders read-only view for non-owner administrators and hides approve/reject buttons', async () => {
    // Mock non-owner admin
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 2,
        email: 'company_admin@example.com',
        full_name: 'Company Admin',
        is_active: true,
        is_superuser: false,
        is_primary_owner: false,
        roles: [{ id: 2, name: 'company_admin' }],
        created_at: '2026-11-15T00:00:00Z',
        primary_dashboard: 'company',
      },
      token: 'mock-jwt-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      joinOrganization: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(true),
      hasAnyRole: vi.fn().mockReturnValue(true),
    });

    render(
      <MemoryRouter>
        <OwnerAccessGovernanceSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Standard Platform Admin View \(Read Only\)/i)).toBeInTheDocument();
    });

    // Inspect button should exist, but Approve/Reject should NOT be rendered
    expect(screen.getAllByTitle('Inspect Details').length).toBeGreaterThan(0);
    expect(screen.queryByTitle('Approve Request')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Reject Request')).not.toBeInTheDocument();
  });
});
