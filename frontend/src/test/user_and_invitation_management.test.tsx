import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserAndInvitationManagementSection } from '../features/dashboard/UserAndInvitationManagementSection';
import { authApi } from '../shared/api/auth';
import { User, InvitationRead, Role, OrganizationItem } from '../shared/types/auth';
import i18n from '../i18n/config';

vi.mock('../shared/api/auth', () => ({
  authApi: {
    listUsers: vi.fn(),
    listInvitations: vi.fn(),
    listRoles: vi.fn(),
    listOrganizations: vi.fn(),
    createUser: vi.fn(),
    createInvitation: vi.fn(),
    revokeInvitation: vi.fn(),
    updateUserStatus: vi.fn(),
  },
}));

const mockUsers: User[] = [
  {
    id: 1,
    email: 'muhammadyusufusmonov011@gmail.com',
    full_name: 'Muhammadyusuf Usmonov',
    is_active: true,
    is_superuser: true,
    is_primary_owner: true,
    primary_dashboard: 'platform',
    roles: [{ id: 1, name: 'platform_super_admin' }],
    organization_id: 1,
    organization_name: 'Platform Engineering HQ',
    created_at: '2026-11-15T12:00:00Z',
  },
  {
    id: 2,
    email: 'tech.lead@initech.corp',
    full_name: 'Tech Lead Initech',
    is_active: true,
    is_superuser: false,
    is_primary_owner: false,
    primary_dashboard: 'company',
    roles: [{ id: 2, name: 'company_admin' }],
    organization_id: 2,
    organization_name: 'Initech Global',
    created_at: '2026-11-15T13:00:00Z',
  },
];

const mockInvitations: InvitationRead[] = [
  {
    id: 101,
    token_prefix: 'sp_inv_abc123',
    role_id: 3,
    role_name: 'it_admin',
    organization_id: 2,
    organization_name: 'Initech Global',
    invited_email: 'newbie@initech.corp',
    is_revoked: false,
    is_valid: true,
    max_uses: 1,
    uses_count: 0,
    expires_at: '2026-11-25T12:00:00Z',
    created_at: '2026-11-15T14:00:00Z',
  },
];

const mockRoles: Role[] = [
  { id: 1, name: 'platform_super_admin', description: 'Platform Super Admin' },
  { id: 2, name: 'company_admin', description: 'Company Admin' },
  { id: 3, name: 'it_admin', description: 'IT Administrator' },
  { id: 4, name: 'support', description: 'Support Technician' },
  { id: 5, name: 'executive', description: 'Executive Viewer' },
  { id: 6, name: 'employee', description: 'Company Employee' },
];

const mockOrgs: OrganizationItem[] = [
  { id: 1, name: 'Platform Engineering HQ', slug: 'hq', domain: 'servicepulse.local', is_active: true, max_devices: 100 },
  { id: 2, name: 'Initech Global', slug: 'initech', domain: 'initech.corp', is_active: true, max_devices: 100 },
];

describe('UserAndInvitationManagementSection Component', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.clearAllMocks();
    vi.mocked(authApi.listUsers).mockResolvedValue(mockUsers);
    vi.mocked(authApi.listInvitations).mockResolvedValue(mockInvitations);
    vi.mocked(authApi.listRoles).mockResolvedValue(mockRoles);
    vi.mocked(authApi.listOrganizations).mockResolvedValue(mockOrgs);
  });

  it('renders Active Users Directory with Primary Owner badge and role indicators', async () => {
    render(<UserAndInvitationManagementSection scope="platform" />);

    await waitFor(() => {
      expect(screen.getByText('muhammadyusufusmonov011@gmail.com')).toBeInTheDocument();
      expect(screen.getByText('Muhammadyusuf Usmonov')).toBeInTheDocument();
      expect(screen.getByText('tech.lead@initech.corp')).toBeInTheDocument();
      expect(screen.getByText('Tech Lead Initech')).toBeInTheDocument();
    });

    // Check Primary Owner Pill
    expect(screen.getByText('PRIMARY OWNER')).toBeInTheDocument();

    // Check Organizations rendered
    expect(screen.getByText('Platform Engineering HQ')).toBeInTheDocument();
    expect(screen.getAllByText('Initech Global').length).toBeGreaterThan(0);
  });

  it('filters users directory by search query and role filter', async () => {
    render(<UserAndInvitationManagementSection scope="platform" />);

    await waitFor(() => {
      expect(screen.getByText('Muhammadyusuf Usmonov')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search by name, email, or role/i);
    fireEvent.change(searchInput, { target: { value: 'Initech' } });

    expect(screen.queryByText('Muhammadyusuf Usmonov')).not.toBeInTheDocument();
    expect(screen.getByText('Tech Lead Initech')).toBeInTheDocument();
  });

  it('opens Direct User Provisioning modal and creates a user successfully', async () => {
    const user = userEvent.setup();
    const newUser: User = {
      id: 3,
      email: 'new.admin@initech.corp',
      full_name: 'New Administrator',
      is_active: true,
      is_superuser: false,
      is_primary_owner: false,
      primary_dashboard: 'sysadmin',
      roles: [{ id: 3, name: 'it_admin' }],
      organization_id: 2,
      organization_name: 'Initech Global',
      created_at: '2026-11-15T15:00:00Z',
    };
    vi.mocked(authApi.createUser).mockResolvedValueOnce(newUser);

    render(<UserAndInvitationManagementSection scope="platform" />);

    await waitFor(() => {
      expect(screen.getByText('muhammadyusufusmonov011@gmail.com')).toBeInTheDocument();
    });

    // Click "+ Create User"
    const createBtn = screen.getByText('+ Create User');
    await user.click(createBtn);

    // Modal should be open
    expect(screen.getByText('Direct User Account Provisioning')).toBeInTheDocument();

    // Fill form
    const fullNameInput = screen.getByPlaceholderText('e.g. John Doe / Jahongir Alimov');
    const emailInput = screen.getByPlaceholderText('user@example.com');
    const passwordInput = screen.getByPlaceholderText('Minimum 8 chars, 1 uppercase, 1 digit');

    await user.type(fullNameInput, 'New Administrator');
    await user.type(emailInput, 'new.admin@initech.corp');
    await user.type(passwordInput, 'Secr3tP@ssword');

    // Submit
    const submitBtn = screen.getByRole('button', { name: 'Provision User' });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(authApi.createUser).toHaveBeenCalledWith(
        expect.objectContaining({
          email: 'new.admin@initech.corp',
          full_name: 'New Administrator',
          password: 'Secr3tP@ssword',
        })
      );
    });
  });

  it('switches to Issued Invitations tab and generates an invitation token with copyable banner', async () => {
    const user = userEvent.setup();
    const newInvitation: InvitationRead = {
      id: 102,
      token_prefix: 'sp_inv_test_sec',
      role_id: 3,
      role_name: 'it_admin',
      organization_id: 2,
      organization_name: 'Initech Global',
      invited_email: 'invitee@initech.corp',
      is_revoked: false,
      is_valid: true,
      max_uses: 1,
      uses_count: 0,
      expires_at: '2026-11-22T12:00:00Z',
      created_at: '2026-11-15T15:30:00Z',
    };
    vi.mocked(authApi.createInvitation).mockResolvedValueOnce({
      raw_token: 'sp_inv_test_secret_token_12345',
      invitation: newInvitation,
    });

    render(<UserAndInvitationManagementSection scope="platform" />);

    await waitFor(() => {
      expect(screen.getByText('Issued Invitations')).toBeInTheDocument();
    });

    // Switch to Invitations tab
    const invitesTab = screen.getByText('Issued Invitations');
    await user.click(invitesTab);

    // Verify existing invitation is shown
    expect(screen.getByText(/sp_inv_abc123/)).toBeInTheDocument();
    expect(screen.getByText('newbie@initech.corp')).toBeInTheDocument();

    // Click "+ Issue Invitation"
    const issueBtn = screen.getByText('+ Issue Invitation');
    await user.click(issueBtn);

    expect(screen.getByText('Cryptographic Invitation Issuance')).toBeInTheDocument();

    // Select role
    const selectRole = screen.getByTestId('invite-role-select');
    fireEvent.change(selectRole, { target: { value: 'it_admin' } });

    // Submit
    const submitBtn = screen.getByRole('button', { name: 'Generate Invitation Token' });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(authApi.createInvitation).toHaveBeenCalledWith(
        expect.objectContaining({
          role_name: 'it_admin',
        })
      );
    });

    // Verification banner for the newly generated token should be visible
    await waitFor(() => {
      expect(screen.getByText('sp_inv_test_secret_token_12345')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Copy Token/i })).toBeInTheDocument();
    });
  });

  it('respects company scope without fetching global organizations list', async () => {
    render(
      <UserAndInvitationManagementSection
        scope="company"
        currentOrganizationId={2}
        currentOrganizationName="Initech Global"
      />
    );

    await waitFor(() => {
      expect(screen.getAllByText('Initech Global').length).toBeGreaterThan(0);
    });

    // listOrganizations should NOT have been called in company scope
    expect(authApi.listOrganizations).not.toHaveBeenCalled();
    // listUsers was called with organization_id filter
    expect(authApi.listUsers).toHaveBeenCalledWith(0, 200, 2);
    expect(authApi.listInvitations).toHaveBeenCalledWith(2);
  });
});
