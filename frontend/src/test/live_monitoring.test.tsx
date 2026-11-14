/**
 * ServicePulse - Live Monitoring Frontend Tests
 * Author: Muhammadyusuf Usmonov
 * Academic Purpose: AT-Servis BMI
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LiveMonitoringPage } from '../features/monitoring/LiveMonitoringPage';
import { inventoryApi } from '../shared/api/inventory';
import type { DeviceRead } from '../shared/types/inventory';
import * as AuthContextModule from '../features/auth/AuthContext';
import * as WSRealtimeModule from '../features/monitoring/useRealtimeMonitoring';
import '../i18n/config';

vi.mock('../shared/api/inventory', () => ({
  inventoryApi: {
    listDevices: vi.fn(),
  },
}));

vi.mock('../features/monitoring/useRealtimeMonitoring', () => ({
  useRealtimeMonitoring: vi.fn(),
}));

describe('LiveMonitoringPage Component (STEP 5.3.1)', () => {
  let queryClient: QueryClient;

  const mockDevices: DeviceRead[] = [
    {
      id: 1,
      organization_id: 1,
      room_id: 1,
      name: 'Core Router 01',
      hostname: 'router-01',
      device_type: 'router',
      ip_address: '192.168.1.1',
      mac_address: '00:11:22:33:44:55',
      status: 'online',
      consecutive_failures: 0,
      is_monitored: true,
      is_sample_data: false,
      last_seen: '2026-11-14T10:00:00Z',
      created_at: '2026-11-01T00:00:00Z',
    },
    {
      id: 2,
      organization_id: 1,
      room_id: 1,
      name: 'Windows Server 2022',
      hostname: 'win-srv-2022',
      device_type: 'server',
      ip_address: '192.168.1.10',
      mac_address: '00:11:22:33:44:66',
      status: 'offline',
      consecutive_failures: 5,
      is_monitored: true,
      is_sample_data: false,
      last_seen: '2026-11-14T09:30:00Z',
      created_at: '2026-11-01T00:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 1,
        email: 'sysadmin@servicepulse.uz',
        full_name: 'Sysadmin Test',
        organization_id: 1,
        is_active: true,
        is_superuser: false,
        created_at: '2026-01-01T00:00:00Z',
        roles: [{ id: 1, name: 'it_admin' }],
        primary_dashboard: 'sysadmin',
      },
      hasRole: () => true,
      hasAnyRole: () => true,
      isLoading: false,
      isAuthenticated: true,
      token: 'mock_token',
      login: vi.fn(),
      logout: vi.fn(),
    });

    vi.mocked(inventoryApi.listDevices).mockResolvedValue(mockDevices);

    vi.mocked(WSRealtimeModule.useRealtimeMonitoring).mockReturnValue({
      status: 'connected',
      events: [
        {
          type: 'device:status_change',
          payload: {
            device_id: 2,
            device_name: 'Windows Server 2022',
            old_status: 'online',
            new_status: 'offline',
          },
          timestamp: '2026-11-14T10:05:00Z',
        },
      ],
      lastMessage: null,
      telemetryMap: {
        1: {
          agent_id: 10,
          device_id: 1,
          hostname: 'ROUTER-01',
          cpu_percent: 32.5,
          ram_percent: 45.0,
          disk_percent: 60.0,
          windows_activation_status: 'Licensed',
          windows_defender_status: 'Healthy',
          recorded_at: '2026-11-14T10:05:00Z',
        },
      },
      clearEvents: vi.fn(),
      reconnect: vi.fn(),
    });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <LiveMonitoringPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders Live Monitoring header and Connected status indicator', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Live Fleet Monitoring|Jonli Flot Monitoringi|Живой мониторинг/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Connected|Ulangan|Подключено/i)).toBeInTheDocument();
  });

  it('displays correct KPI summary counters for fleet devices', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Core Router 01')).toBeInTheDocument();
    });

    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Windows Server 2022')).toBeInTheDocument();
  });

  it('renders live telemetry metrics for monitored devices', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('32.5%')).toBeInTheDocument(); // CPU
    });

    expect(screen.getByText('45.0%')).toBeInTheDocument(); // RAM
    expect(screen.getByText('60.0%')).toBeInTheDocument(); // Disk
  });

  it('switches between fleet telemetry tab and live event bus tab', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Core Router 01')).toBeInTheDocument();
    });

    const eventsTab = screen.getByText(/Live Event Stream|Jonli Hodisalar Oqimi|Поток событий/i);
    fireEvent.click(eventsTab);

    await waitFor(() => {
      expect(screen.getByText(/device:status_change/i)).toBeInTheDocument();
    });
  });
});
