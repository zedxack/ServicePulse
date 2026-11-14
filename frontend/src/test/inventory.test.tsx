import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InventoryExplorerPage } from '../features/inventory/InventoryExplorerPage';
import { inventoryApi } from '../shared/api/inventory';
import * as AuthContextModule from '../features/auth/AuthContext';
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

describe('InventoryExplorerPage Component & Module 5.2.1', () => {
  let queryClient: QueryClient;

  const mockTree = {
    total_buildings: 1,
    total_floors: 1,
    total_rooms: 1,
    total_devices: 1,
    buildings: [
      {
        id: 1,
        organization_id: 1,
        name: 'Main Lab Building',
        code: 'BLD-01',
        address: 'Amir Temur 108',
        description: 'Main campus facility',
        is_sample_data: false,
        created_at: '2026-11-14T00:00:00Z',
        floors: [
          {
            id: 1,
            building_id: 1,
            level: 2,
            name: 'Network Floor',
            description: 'Lab 204',
            is_sample_data: false,
            created_at: '2026-11-14T00:00:00Z',
            rooms: [
              {
                id: 1,
                floor_id: 1,
                room_number: '204',
                name: 'Cisco Routing Lab',
                description: 'Room 204',
                is_sample_data: false,
                created_at: '2026-11-14T00:00:00Z',
                devices: [
                  {
                    id: 10,
                    name: 'Core Switch 01',
                    hostname: 'sw-core-01.local',
                    ip_address: '192.168.10.1',
                    device_type: 'switch',
                    operating_system: 'Cisco IOS',
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
      id: 10,
      name: 'Core Switch 01',
      hostname: 'sw-core-01.local',
      ip_address: '192.168.10.1',
      device_type: 'switch',
      operating_system: 'Cisco IOS',
      is_monitored: true,
      is_sample_data: false,
      status: 'online',
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
        email: 'admin@servicepulse.uz',
        full_name: 'Admin User',
        is_active: true,
        is_superuser: true,
        roles: [{ id: 1, name: 'platform_super_admin' }],
        created_at: '2026-11-14T00:00:00Z',
        primary_dashboard: 'platform',
      },
      token: 'fake-token',
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
        device_id: 10,
        check_type: 'icmp',
        target: '192.168.10.1',
        is_success: true,
        response_time_ms: 1.5,
        checked_at: '2026-11-14T10:00:00Z',
      },
    ]);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <InventoryExplorerPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders hierarchy tree view with buildings, floors, rooms and device badges', async () => {
    renderComponent();

    // Verify stats
    await waitFor(() => {
      expect(screen.getByText('Main Lab Building')).toBeInTheDocument();
    });
    expect(screen.getByText('BLD-01')).toBeInTheDocument();

    // Expand building
    fireEvent.click(screen.getByText('Main Lab Building'));

    // Verify floor appears
    await waitFor(() => {
      expect(screen.getByText(/Level 2: Network Floor/i)).toBeInTheDocument();
    });

    // Expand floor
    fireEvent.click(screen.getByText(/Level 2: Network Floor/i));

    // Verify room and device appear
    await waitFor(() => {
      expect(screen.getByText(/204 • Cisco Routing Lab/i)).toBeInTheDocument();
      expect(screen.getByText('Core Switch 01')).toBeInTheDocument();
    });
  });

  it('switches to list view and filters devices', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Main Lab Building')).toBeInTheDocument();
    });

    // Switch to list view
    const listTab = screen.getByRole('button', { name: /Qurilmalar Ro'yxati|Device Inventory/i });
    fireEvent.click(listTab);

    await waitFor(() => {
      expect(screen.getByText('sw-core-01.local')).toBeInTheDocument();
      expect(screen.getByText('192.168.10.1')).toBeInTheDocument();
    });
  });

  it('opens device detail modal when clicking a device', async () => {
    renderComponent();

    // Switch to list view and click details
    const listTab = screen.getByRole('button', { name: /Qurilmalar Ro'yxati|Device Inventory/i });
    fireEvent.click(listTab);

    await waitFor(() => {
      expect(screen.getByText('sw-core-01.local')).toBeInTheDocument();
    });

    const detailBtn = screen.getByRole('button', { name: /Batafsil|Details/i });
    fireEvent.click(detailBtn);

    // Modal should open
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Tarmoq Sinovlari Tarixi|Network Probe History/i })).toBeInTheDocument();
    });

    // Switch to network probes tab
    fireEvent.click(screen.getByRole('button', { name: /Tarmoq Sinovlari Tarixi|Network Probe History/i }));
    await waitFor(() => {
      expect(screen.getByText(/1.5 ms/i)).toBeInTheDocument();
    });
  });

  it('hides add device button when user lacks editor role', async () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 2,
        email: 'employee@servicepulse.uz',
        full_name: 'Regular Employee',
        is_active: true,
        is_superuser: false,
        roles: [{ id: 6, name: 'employee' }],
        created_at: '2026-11-14T00:00:00Z',
        primary_dashboard: 'employee',
      },
      token: 'fake-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(false),
      hasAnyRole: vi.fn().mockReturnValue(false),
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Main Lab Building')).toBeInTheDocument();
    });

    // Add button should not be rendered
    expect(screen.queryByRole('button', { name: /Qurilma Qo'shish|Add Device/i })).not.toBeInTheDocument();
  });
});
