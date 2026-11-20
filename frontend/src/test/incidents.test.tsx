import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { IncidentsPage } from '../features/incidents/IncidentsPage';
import { incidentsApi } from '../shared/api/incidents';
import * as AuthContextModule from '../features/auth/AuthContext';
import '../i18n/config';

vi.mock('../shared/api/incidents', () => ({
  incidentsApi: {
    listIncidents: vi.fn(),
    getIncident: vi.fn(),
    getIncidentEvents: vi.fn(),
    acknowledgeIncident: vi.fn(),
    assignIncident: vi.fn(),
    resolveIncident: vi.fn(),
    listRemediationExecutions: vi.fn(),
  },
}));

describe('IncidentsPage Component & Module 5.2.2', () => {
  let queryClient: QueryClient;

  const mockIncidentsResponse = {
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
  };

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
        full_name: 'IT Admin User',
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

    vi.mocked(incidentsApi.listIncidents).mockResolvedValue(mockIncidentsResponse);
    vi.mocked(incidentsApi.acknowledgeIncident).mockResolvedValue({
      ...mockIncidentsResponse.items[0],
      status: 'acknowledged',
    });
    vi.mocked(incidentsApi.resolveIncident).mockResolvedValue({
      ...mockIncidentsResponse.items[0],
      status: 'resolved',
    });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <IncidentsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders incidents list with severity and status indicators', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Core Switch ICMP Outage')).toBeInTheDocument();
      expect(screen.getByText('High CPU Utilization on Server 02')).toBeInTheDocument();
    });

    // Check counts
    expect(screen.getByText('#101')).toBeInTheDocument();
    expect(screen.getByText('#102')).toBeInTheDocument();
  });

  it('calls acknowledge endpoint when acknowledge button is clicked', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Core Switch ICMP Outage')).toBeInTheDocument();
    });

    const ackButtons = screen.getAllByRole('button', { name: /Qabul qilish|Acknowledge/i });
    expect(ackButtons.length).toBeGreaterThan(0);

    fireEvent.click(ackButtons[0]);

    await waitFor(() => {
      expect(incidentsApi.acknowledgeIncident).toHaveBeenCalledWith(101, {
        notes: 'Quick ack from list',
      });
    });
  });

  it('opens resolve modal and requires resolution notes before resolving', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Core Switch ICMP Outage')).toBeInTheDocument();
    });

    const resolveButtons = screen.getAllByRole('button', { name: /Hal qilish|Resolve/i });
    fireEvent.click(resolveButtons[0]);

    // Modal should appear
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Avariya qanday bartaraf etilganini yozing|Describe how this incident was resolved/i)).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Avariya qanday bartaraf etilganini yozing|Describe how this incident was resolved/i);
    fireEvent.change(textarea, { target: { value: 'Restarted switch port' } });

    const submitBtn = screen.getAllByRole('button', { name: /Hal qilish|Resolve/i }).find((btn) => btn.getAttribute('type') === 'submit')!;
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(incidentsApi.resolveIncident).toHaveBeenCalledWith(101, {
        resolution_notes: 'Restarted switch port',
      });
    });
  });
});
