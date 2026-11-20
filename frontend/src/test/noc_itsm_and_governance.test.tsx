import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { IncidentsPage } from '../features/incidents/IncidentsPage';
import { HelpdeskPage } from '../features/tickets/HelpdeskPage';
import { AlertCenterPage } from '../features/alerts/AlertCenterPage';
import { SoftwarePage } from '../features/software/SoftwarePage';
import { OwnerAccessGovernanceSection } from '../features/dashboard/OwnerAccessGovernanceSection';
import { incidentsApi } from '../shared/api/incidents';
import { ticketsApi } from '../shared/api/tickets';
import { getAlerts, getUnreadAlertCount } from '../shared/api/alerts';
import { softwareApi } from '../shared/api/software';
import { authApi } from '../shared/api/auth';
import * as AuthContextModule from '../features/auth/AuthContext';
import '../i18n/config';

vi.mock('../shared/api/incidents', () => ({
  incidentsApi: {
    listIncidents: vi.fn(),
    acknowledgeIncident: vi.fn(),
    resolveIncident: vi.fn(),
  },
}));

vi.mock('../shared/api/tickets', () => ({
  ticketsApi: {
    listTickets: vi.fn(),
  },
}));

vi.mock('../shared/api/alerts', () => ({
  getAlerts: vi.fn(),
  getUnreadAlertCount: vi.fn(),
  markAlertRead: vi.fn(),
  markAllAlertsRead: vi.fn(),
}));

vi.mock('../shared/api/software', () => ({
  softwareApi: {
    getSoftwareCatalog: vi.fn(),
    listSoftwareRequests: vi.fn(),
  },
}));

vi.mock('../shared/api/auth', () => ({
  authApi: {
    listAccessRequests: vi.fn(),
    getAccessRequestStats: vi.fn(),
    approveAccessRequest: vi.fn(),
    rejectAccessRequest: vi.fn(),
  },
}));

describe('NOC ITSM, War Room & Governance Command Center (Stage 4)', () => {
  let queryClient: QueryClient;

  const mockUser = {
    id: 1,
    email: 'primary_owner@servicepulse.uz',
    full_name: 'Primary Owner Admin',
    is_active: true,
    is_superuser: true,
    is_primary_owner: true,
    roles: [{ id: 1, name: 'platform_super_admin' }],
    created_at: '2026-11-14T00:00:00Z',
    primary_dashboard: 'platform',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: mockUser,
      token: 'fake-token-stage4',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(true),
      hasAnyRole: vi.fn().mockReturnValue(true),
    });
  });

  const renderWithProviders = (ui: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          {ui}
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it('renders Incident War Room telemetry strip and quick severity pills', async () => {
    vi.mocked(incidentsApi.listIncidents).mockResolvedValue({
      total: 2,
      items: [
        {
          id: 101,
          organization_id: 1,
          device_id: 10,
          fingerprint: 'icmp_fail_sw_01',
          title: 'Core Switch ICMP Outage',
          description: 'Consecutive probe timeouts on 192.168.10.1',
          severity: 'critical',
          status: 'open',
          occurrence_count: 5,
          first_seen_at: '2026-11-14T08:00:00Z',
          last_seen_at: '2026-11-14T08:05:00Z',
          assigned_to_user_id: null,
          events: [],
          created_at: '2026-11-14T08:00:00Z',
        },
        {
          id: 102,
          organization_id: 1,
          device_id: 12,
          fingerprint: 'high_cpu_srv_02',
          title: 'High CPU Utilization on Server 02',
          description: 'CPU sustained at 98%',
          severity: 'warning',
          status: 'acknowledged',
          occurrence_count: 2,
          first_seen_at: '2026-11-14T09:00:00Z',
          last_seen_at: '2026-11-14T09:10:00Z',
          assigned_to_user_id: 1,
          events: [],
          created_at: '2026-11-14T09:00:00Z',
        },
      ],
    });

    renderWithProviders(<IncidentsPage />);

    // Wait for data load
    await waitFor(() => {
      expect(screen.getByText('Core Switch ICMP Outage')).toBeInTheDocument();
    });

    // Verify War Room Telemetry Header
    expect(screen.getByText(/INCIDENT WAR ROOM/i)).toBeInTheDocument();
    expect(screen.getByText(/TRIAGE: ACTIVE/i)).toBeInTheDocument();
    expect(screen.getByText(/CRITICAL OUTAGES/i)).toBeInTheDocument();

    // Verify quick severity filter pills
    expect(screen.getByRole('button', { name: /ALL SEV/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /CRIT \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /WARN/i })).toBeInTheDocument();

    // Verify incident titles rendered in high density table
    expect(screen.getByText('High CPU Utilization on Server 02')).toBeInTheDocument();

    // Click critical severity pill
    fireEvent.click(screen.getByRole('button', { name: /CRIT \(1\)/i }));
    await waitFor(() => {
      expect(screen.getByText('Core Switch ICMP Outage')).toBeInTheDocument();
    });
  });

  it('renders Helpdesk Queue with ITSM telemetry strip and quick status pills', async () => {
    vi.mocked(ticketsApi.listTickets).mockResolvedValue([
      {
        id: 201,
        organization_id: 1,
        author_id: 10,
        assigned_to_id: 1,
        title: 'Network printer unreachable in Finance',
        description: 'Cannot print invoices since 9 AM.',
        category: 'hardware',
        priority: 'urgent',
        status: 'open',
        device_id: null,
        comments: [],
        created_at: '2026-11-14T09:00:00Z',
        updated_at: '2026-11-14T09:30:00Z',
      },
      {
        id: 202,
        organization_id: 1,
        author_id: 11,
        assigned_to_id: null,
        title: 'VPN credential reset request',
        description: 'Employee locked out after 3 invalid attempts.',
        category: 'access',
        priority: 'medium',
        status: 'resolved',
        device_id: null,
        comments: [],
        created_at: '2026-11-14T10:00:00Z',
        updated_at: '2026-11-14T11:00:00Z',
      },
    ]);

    renderWithProviders(<HelpdeskPage />);

    // Wait for data load
    await waitFor(() => {
      expect(screen.getByText('Network printer unreachable in Finance')).toBeInTheDocument();
    });

    // Verify ITSM Service Desk Telemetry Strip
    expect(screen.getByText(/ITSM SERVICE DESK/i)).toBeInTheDocument();

    // Verify filter pills
    expect(screen.getByRole('button', { name: /ALL \(2\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /OPEN \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /RESOLVED \(1\)/i })).toBeInTheDocument();

    // Verify ticket records rendered
    expect(screen.getByText('VPN credential reset request')).toBeInTheDocument();
    expect(screen.getByText('#201')).toBeInTheDocument();
    expect(screen.getByText('#202')).toBeInTheDocument();
  });

  it('renders SOC Alert Triage with stream indicator and contextual incident links', async () => {
    vi.mocked(getAlerts).mockResolvedValue({
      total: 1,
      unread_count: 1,
      items: [
        {
          id: 701,
          organization_id: 1,
          user_id: null,
          target_role: null,
          title: 'High Temperature Detected on Switch 01',
          message: 'Sensor alert: temperature exceeded 85C threshold.',
          severity: 'critical',
          category: 'device',
          fingerprint: 'temp_crit_701',
          is_read: false,
          is_dismissed: false,
          read_at: null,
          created_at: '2026-11-14T11:00:00Z',
          data: { device_id: 10, incident_id: 102 },
        },
      ],
    });
    vi.mocked(getUnreadAlertCount).mockResolvedValue({ unread_count: 1 });

    renderWithProviders(<AlertCenterPage />);

    // Wait for alerts to load
    await waitFor(() => {
      expect(screen.getByText('High Temperature Detected on Switch 01')).toBeInTheDocument();
    });

    // Verify SOC Alert Triage header strip
    expect(screen.getByText(/SOC ALERT TRIAGE/i)).toBeInTheDocument();
    expect(screen.getByText(/QUEUE: STREAM/i)).toBeInTheDocument();
    expect(screen.getByText(/30d RETENTION/i)).toBeInTheDocument();

    // Verify alert contextual deep links (multilingual regex)
    expect(screen.getByText(/View Device #10|Qurilmani ko'rish #10|Открыть устройство #10/i)).toBeInTheDocument();
    expect(screen.getByText(/View Incident #102|Hodisani ko'rish #102|Открыть инцидент #102/i)).toBeInTheDocument();
  });

  it('renders Software Governance zero-trust telemetry strip and catalog packages', async () => {
    vi.mocked(softwareApi.getSoftwareCatalog).mockResolvedValue([
      'Google Chrome',
      'Visual Studio Code',
      'Wireshark',
    ]);
    vi.mocked(softwareApi.listSoftwareRequests).mockResolvedValue([]);

    renderWithProviders(<SoftwarePage />);

    // Wait for catalog load
    await waitFor(() => {
      expect(screen.getByText('Google Chrome')).toBeInTheDocument();
    });

    // Verify Software Asset Control Strip
    expect(screen.getByText(/SOFTWARE ASSET CONTROL/i)).toBeInTheDocument();
    expect(screen.getByText(/3 APPROVED/i)).toBeInTheDocument();
    expect(screen.getByText(/ZERO-TRUST ENFORCEMENT/i)).toBeInTheDocument();

    // Verify packages
    expect(screen.getByText('Visual Studio Code')).toBeInTheDocument();
    expect(screen.getByText('Wireshark')).toBeInTheDocument();
  });

  it('renders Authoritative Primary Owner Access Governance controls and metric cards', async () => {
    vi.mocked(authApi.listAccessRequests).mockResolvedValue([
      {
        id: 501,
        organization_id: 1,
        applicant_email: 'new_engineer@servicepulse.uz',
        applicant_full_name: 'New Test Engineer',
        request_type: 'organization_membership',
        organization_name: 'Acme Corp NOC',
        target_role_name: 'technician',
        status: 'pending',
        rejection_reason: null,
        reviewed_by_id: null,
        reviewed_at: null,
        created_at: '2026-11-14T12:00:00Z',
      },
    ]);
    vi.mocked(authApi.getAccessRequestStats).mockResolvedValue({
      total_count: 5,
      pending_count: 1,
      approved_count: 3,
      rejected_count: 1,
    });

    renderWithProviders(<OwnerAccessGovernanceSection />);

    // Verify Authoritative Primary Owner Banner
    await waitFor(() => {
      expect(screen.getByText(/Authoritative Primary Owner Access Active/i)).toBeInTheDocument();
    });

    // Verify Stats Summary Cards
    expect(screen.getByText(/Pending Review/i)).toBeInTheDocument();
    expect(screen.getByText(/ACTION REQUIRED/i)).toBeInTheDocument();

    // Verify applicant row in table
    expect(screen.getByText('New Test Engineer')).toBeInTheDocument();
    expect(screen.getByText('new_engineer@servicepulse.uz')).toBeInTheDocument();
    expect(screen.getByText('Acme Corp NOC')).toBeInTheDocument();
    expect(screen.getByText('#501')).toBeInTheDocument();

    // Verify action buttons present for owner
    expect(screen.getByTitle('Inspect Details')).toBeInTheDocument();
    expect(screen.getByTitle('Approve Request')).toBeInTheDocument();
    expect(screen.getByTitle('Reject Request')).toBeInTheDocument();
  });
});
