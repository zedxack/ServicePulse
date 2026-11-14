import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SoftwarePage } from '../features/software/SoftwarePage';
import { softwareApi } from '../shared/api/software';
import { inventoryApi } from '../shared/api/inventory';
import type { DeviceRead } from '../shared/types/inventory';
import * as AuthContextModule from '../features/auth/AuthContext';
import '../i18n/config';

vi.mock('../shared/api/software', () => ({
  softwareApi: {
    getSoftwareCatalog: vi.fn(),
    listSoftwareRequests: vi.fn(),
    getSoftwareRequest: vi.fn(),
    submitSoftwareRequest: vi.fn(),
    approveSoftwareRequest: vi.fn(),
    rejectSoftwareRequest: vi.fn(),
  },
}));

vi.mock('../shared/api/inventory', () => ({
  inventoryApi: {
    listDevices: vi.fn(),
  },
}));

describe('SoftwarePage Component & Module 5.2.4', () => {
  let queryClient: QueryClient;

  const mockCatalog = ['Google Chrome', 'Visual Studio Code', 'Git', 'Wireshark'];

  const mockRequests = [
    {
      id: 301,
      organization_id: 1,
      user_id: 10,
      device_id: 5,
      software_name: 'Visual Studio Code',
      software_version: 'Latest',
      reason: 'Required for AT-Servis laboratory python development',
      status: 'pending',
      reviewed_by_user_id: null,
      review_notes: null,
      reviewed_at: null,
      created_at: '2026-11-14T08:00:00Z',
    },
    {
      id: 302,
      organization_id: 1,
      user_id: 10,
      device_id: 5,
      software_name: 'Google Chrome',
      software_version: 'Latest',
      reason: 'Web interface testing',
      status: 'approved',
      reviewed_by_user_id: 1,
      review_notes: 'Approved standard package',
      reviewed_at: '2026-11-14T08:30:00Z',
      created_at: '2026-11-14T07:00:00Z',
    },
  ];

  const mockDevices: DeviceRead[] = [
    {
      id: 5,
      organization_id: 1,
      room_id: 1,
      name: 'Lab Workstation 05',
      hostname: 'ws-lab-05.local',
      ip_address: '192.168.10.55',
      mac_address: '00:11:22:33:44:55',
      device_type: 'workstation',
      status: 'online',
      is_monitored: true,
      is_sample_data: false,
      consecutive_failures: 0,
      created_at: '2026-11-14T00:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 1,
        email: 'it_admin@servicepulse.uz',
        full_name: 'IT Admin Approver',
        is_active: true,
        is_superuser: false,
        roles: [{ id: 4, name: 'it_admin' }],
        created_at: '2026-11-14T00:00:00Z',
        primary_dashboard: 'sysadmin',
      },
      token: 'fake-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(true),
      hasAnyRole: vi.fn().mockReturnValue(true),
    });

    vi.mocked(softwareApi.getSoftwareCatalog).mockResolvedValue(mockCatalog);
    vi.mocked(softwareApi.listSoftwareRequests).mockResolvedValue(mockRequests);
    vi.mocked(inventoryApi.listDevices).mockResolvedValue(mockDevices);
    vi.mocked(softwareApi.submitSoftwareRequest).mockResolvedValue({
      id: 303,
      organization_id: 1,
      user_id: 10,
      device_id: 5,
      software_name: 'Git',
      reason: 'Required for version control',
      status: 'pending',
      created_at: '2026-11-14T09:00:00Z',
    });
    vi.mocked(softwareApi.approveSoftwareRequest).mockResolvedValue({
      ...mockRequests[0],
      status: 'approved',
      reviewed_by_user_id: 1,
    });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SoftwarePage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders software catalog with packages and security notice', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Google Chrome')).toBeInTheDocument();
      expect(screen.getByText('Visual Studio Code')).toBeInTheDocument();
      expect(screen.getByText('Wireshark')).toBeInTheDocument();
    });

    // Check security architecture notice
    expect(screen.getByText(/Xavfsizlik eslatmasi|Security Notice/i)).toBeInTheDocument();
  });

  it('switches to requests tab and allows IT admin to approve pending request', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Google Chrome')).toBeInTheDocument();
    });

    const requestsTab = screen.getByRole('button', { name: /O'rnatish So'rovlari|Installation Requests/i });
    fireEvent.click(requestsTab);

    await waitFor(() => {
      expect(screen.getByText('Required for AT-Servis laboratory python development')).toBeInTheDocument();
    });

    const approveButtons = screen.getAllByRole('button', { name: /Tasdiqlash|Approve/i });
    fireEvent.click(approveButtons[0]);

    // Modal opens
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Tasdiqlash yoki rad etish sababini yozing|Provide review reasoning/i)).toBeInTheDocument();
    });

    const submitApproveBtn = screen.getAllByRole('button', { name: /^Tasdiqlash$|^Approve$/i }).find((btn) => btn.getAttribute('type') === 'submit')!;
    fireEvent.click(submitApproveBtn);

    await waitFor(() => {
      expect(softwareApi.approveSoftwareRequest).toHaveBeenCalledWith(301, {
        review_notes: undefined,
      });
    });
  });
});
