/**
 * ServicePulse - Stage 3 NOC RMM & Inventory Inspector Tests
 * Author: Muhammadyusuf Usmonov
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InventoryExplorerPage } from '../features/inventory/InventoryExplorerPage';
import { DeviceDetailModal } from '../features/inventory/DeviceDetailModal';
import { LiveMonitoringPage } from '../features/monitoring/LiveMonitoringPage';
import { SysAdminDashboardPage } from '../features/dashboard/SysAdminDashboardPage';
import { inventoryApi } from '../shared/api/inventory';
import { dashboardApi } from '../shared/api/dashboard';
import * as AuthContextModule from '../features/auth/AuthContext';
import * as WSRealtimeModule from '../features/monitoring/useRealtimeMonitoring';
import '../i18n/config';

vi.mock('../shared/api/inventory', () => ({
  inventoryApi: {
    getInventoryTree: vi.fn(),
    listDevices: vi.fn(),
    getDevice: vi.fn(),
    getDeviceNetworkChecks: vi.fn(),
    createBuilding: vi.fn(),
    createFloor: vi.fn(),
    createRoom: vi.fn(),
    createDevice: vi.fn(),
    listAgents: vi.fn(),
    getAgentTelemetry: vi.fn(),
  },
}));

vi.mock('../shared/api/dashboard', () => ({
  dashboardApi: {
    getSysAdminDashboard: vi.fn(),
  },
}));

vi.mock('../features/monitoring/useRealtimeMonitoring', () => ({
  useRealtimeMonitoring: vi.fn(),
}));

describe('Stage 3 NOC RMM & Engineering Cockpit Tests', () => {
  let queryClient: QueryClient;

  const mockTree = {
    total_buildings: 1,
    total_floors: 1,
    total_rooms: 1,
    total_devices: 2,
    buildings: [
      {
        id: 1,
        organization_id: 1,
        name: 'Datacenter Alpha',
        code: 'DC-01',
        address: 'Core Campus St. 1',
        description: 'Primary datacenter facility',
        is_sample_data: false,
        created_at: '2026-11-14T00:00:00Z',
        floors: [
          {
            id: 1,
            building_id: 1,
            level: 1,
            name: 'Server Hall',
            description: 'Rack Row A',
            is_sample_data: false,
            created_at: '2026-11-14T00:00:00Z',
            rooms: [
              {
                id: 1,
                floor_id: 1,
                room_number: '101',
                name: 'Core Cage',
                description: 'Cisco Routing Cage',
                is_sample_data: false,
                created_at: '2026-11-14T00:00:00Z',
                devices: [
                  {
                    id: 101,
                    name: 'Core Border Router',
                    hostname: 'rtr-border-01.noc',
                    ip_address: '10.0.0.1',
                    device_type: 'router',
                    operating_system: 'Cisco IOS-XE',
                    is_monitored: true,
                    is_sample_data: false,
                    room_id: 1,
                    status: 'online',
                    consecutive_failures: 0,
                    created_at: '2026-11-14T00:00:00Z',
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  };

  const mockDevices = [
    {
      id: 101,
      name: 'Core Border Router',
      hostname: 'rtr-border-01.noc',
      ip_address: '10.0.0.1',
      mac_address: '00:50:56:AB:CD:01',
      device_type: 'router',
      operating_system: 'Cisco IOS-XE',
      is_monitored: true,
      is_sample_data: false,
      status: 'online',
      consecutive_failures: 0,
      created_at: '2026-11-14T00:00:00Z',
    },
    {
      id: 102,
      name: 'Storage SAN Switch',
      hostname: 'sw-san-02.noc',
      ip_address: '10.0.0.2',
      mac_address: '00:50:56:AB:CD:02',
      device_type: 'switch',
      operating_system: 'Brocade Fabric OS',
      is_monitored: true,
      is_sample_data: false,
      status: 'warning',
      consecutive_failures: 1,
      created_at: '2026-11-14T00:00:00Z',
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
        full_name: 'NOC Lead Engineer',
        is_active: true,
        is_superuser: true,
        roles: [{ id: 1, name: 'platform_super_admin' }],
        created_at: '2026-11-14T00:00:00Z',
        primary_dashboard: 'sysadmin',
      },
      token: 'mock-jwt-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(true),
      hasAnyRole: vi.fn().mockReturnValue(true),
    });

    vi.mocked(inventoryApi.getInventoryTree).mockResolvedValue(mockTree);
    vi.mocked(inventoryApi.listDevices).mockResolvedValue(mockDevices);
    vi.mocked(inventoryApi.getDeviceNetworkChecks).mockResolvedValue([
      {
        id: 1,
        device_id: 101,
        check_type: 'icmp',
        target: '10.0.0.1',
        is_success: true,
        response_time_ms: 1.2,
        checked_at: '2026-11-14T10:00:00Z',
      },
    ]);
  });

  it('renders quick status filter pills and filters list view', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <InventoryExplorerPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Datacenter Alpha')).toBeInTheDocument();
    });

    // Switch to list view
    const listTab = screen.getByRole('button', { name: /Qurilmalar Ro'yxati|Device Inventory/i });
    fireEvent.click(listTab);

    // Verify both devices appear in list view
    await waitFor(() => {
      expect(screen.getByText('rtr-border-01.noc')).toBeInTheDocument();
      expect(screen.getByText('sw-san-02.noc')).toBeInTheDocument();
    });

    // Verify quick status pills exist
    expect(screen.getByRole('button', { name: /ALL/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ONLINE/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /WARN/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /OFFLINE/i })).toBeInTheDocument();

    // Click ONLINE pill
    fireEvent.click(screen.getByRole('button', { name: /ONLINE/i }));
    expect(inventoryApi.listDevices).toHaveBeenCalledWith(
      expect.objectContaining({ device_status: 'online' })
    );
  });

  it('opens DeviceDetailModal and inspects Diagnostics Console with CLI ping statistics', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DeviceDetailModal device={mockDevices[0]} onClose={vi.fn()} />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Check header and node info
    expect(screen.getByText('Core Border Router')).toBeInTheDocument();
    expect(screen.getAllByText(/10.0.0.1/).length).toBeGreaterThan(0);
    expect(screen.getByText('00:50:56:AB:CD:01')).toBeInTheDocument();

    // Verify embedded quick CLI snapshot in Info tab
    expect(screen.getByText(/NOC Node Inspector/i)).toBeInTheDocument();

    // Switch to Diagnostics Console tab
    const diagTab = screen.getByRole('button', { name: /Diagnostics Console|Diagnostika Konsoli|Консоль диагностики/i });
    fireEvent.click(diagTab);

    // Verify terminal output
    await waitFor(() => {
      expect(screen.getByText(/ServicePulse Automated Network & Posture Inspector/i)).toBeInTheDocument();
      expect(screen.getByText(/Ping Statistics/i)).toBeInTheDocument();
      expect(screen.getByText(/0% packet loss/i)).toBeInTheDocument();
    });

    // Verify Run Probe button
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Run Probe|Probing.../i })).toBeInTheDocument();
    });
  });

  it('renders Operations Cockpit telemetry pills on SysAdmin Dashboard', async () => {
    vi.mocked(dashboardApi.getSysAdminDashboard).mockResolvedValueOnce({
      timestamp: '2026-11-15T12:00:00Z',
      organization_id: 1,
      total_devices: 42,
      online_devices: 40,
      offline_devices: 0,
      warning_devices: 2,
      unknown_devices: 0,
      active_incidents: 1,
      critical_incidents: 0,
      daily_incidents: 2,
      agents_total: 15,
      agents_active: 15,
      agents_offline: 0,
      devices_by_building: [],
      telemetry_summary: {
        avg_cpu_percent: 18.4,
        avg_ram_percent: 52.1,
        avg_disk_percent: 39.8,
        total_telemetry_records: 500,
      },
      active_outages_count: 0,
      pending_remediations_count: 0,
      verified_remediations_count: 12,
      failed_remediations_count: 0,
      recent_recoveries_count: 12,
    });

    render(
      <MemoryRouter>
        <SysAdminDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/OPERATIONS COCKPIT/i)).toBeInTheDocument();
      expect(screen.getByText(/INGESTION: ACTIVE/i)).toBeInTheDocument();
      expect(screen.getByText('42 Total')).toBeInTheDocument();
      expect(screen.getByText('18.4%')).toBeInTheDocument();
    });
  });

  it('renders Live Monitoring WebSocket stream with color-coded badges', async () => {
    vi.mocked(WSRealtimeModule.useRealtimeMonitoring).mockReturnValue({
      status: 'connected',
      events: [
        {
          type: 'device:status_change',
          payload: {
            device_id: 101,
            device_name: 'Core Border Router',
            old_status: 'warning',
            new_status: 'online',
          },
          timestamp: '2026-11-15T12:00:00Z',
        },
      ],
      lastMessage: null,
      telemetryMap: {
        101: {
          agent_id: 1,
          device_id: 101,
          hostname: 'rtr-border-01.noc',
          cpu_percent: 12.0,
          ram_percent: 34.0,
          disk_percent: 50.0,
          windows_activation_status: 'Licensed',
          windows_defender_status: 'Healthy',
          recorded_at: '2026-11-15T12:00:00Z',
        },
      },
      clearEvents: vi.fn(),
      reconnect: vi.fn(),
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <LiveMonitoringPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/REALTIME STREAM/i)).toBeInTheDocument();
      expect(screen.getByText('Core Border Router')).toBeInTheDocument();
      expect(screen.getByText('12.0%')).toBeInTheDocument();
    });
  });
});
