import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { dashboardApi } from '../shared/api/dashboard';
import { PlatformDashboardPage } from '../features/dashboard/PlatformDashboardPage';
import { CompanyDashboardPage } from '../features/dashboard/CompanyDashboardPage';
import { SysAdminDashboardPage } from '../features/dashboard/SysAdminDashboardPage';
import { ExecutiveDashboardPage } from '../features/dashboard/ExecutiveDashboardPage';
import { EmployeeDashboardPage } from '../features/dashboard/EmployeeDashboardPage';
import '../i18n/config';

vi.mock('../shared/api/dashboard', () => ({
  dashboardApi: {
    getPlatformDashboard: vi.fn(),
    getCompanyDashboard: vi.fn(),
    getSysAdminDashboard: vi.fn(),
    getExecutiveDashboard: vi.fn(),
    getEmployeeDashboard: vi.fn(),
  },
}));

describe('Five Role-Based Dashboard Pages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Platform Super Admin Dashboard with real contract fields', async () => {
    vi.mocked(dashboardApi.getPlatformDashboard).mockResolvedValueOnce({
      timestamp: '2026-11-14T06:00:00Z',
      total_organizations: 3,
      active_organizations: 3,
      inactive_organizations: 0,
      total_platform_users: 15,
      total_platform_devices: 42,
      total_platform_agents: 12,
      global_active_incidents: 1,
      platform_health_status: 'healthy',
      recent_global_audits: [
        {
          id: 1,
          action: 'auth_login_success',
          target_resource: 'user',
          target_id: '1',
          status: 'success',
          created_at: '2026-11-14T05:50:00Z',
        },
      ],
    });

    render(<PlatformDashboardPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/Platforma/i).length).toBeGreaterThan(0);
      expect(screen.getByText('3')).toBeInTheDocument(); // total orgs
      expect(screen.getByText('42')).toBeInTheDocument(); // total devices
      expect(screen.getByText('auth_login_success')).toBeInTheDocument();
    });
  });

  it('renders Company Admin Dashboard with organization quota', async () => {
    vi.mocked(dashboardApi.getCompanyDashboard).mockResolvedValueOnce({
      timestamp: '2026-11-14T06:00:00Z',
      organization_id: 1,
      organization_name: 'TATU AT-Servis Lab',
      total_users: 8,
      total_devices: 18,
      max_devices: 100,
      device_utilization_percent: 18.0,
      total_buildings: 2,
      active_incidents: 0,
      recent_org_audits: [],
    });

    render(<CompanyDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('TATU AT-Servis Lab')).toBeInTheDocument();
      expect(screen.getByText('18')).toBeInTheDocument(); // total devices
      expect(screen.getByText('/ 100 max')).toBeInTheDocument();
    });
  });

  it('renders SysAdmin Dashboard with live telemetry and building status', async () => {
    vi.mocked(dashboardApi.getSysAdminDashboard).mockResolvedValueOnce({
      timestamp: '2026-11-14T06:00:00Z',
      organization_id: 1,
      total_devices: 15,
      online_devices: 12,
      offline_devices: 2,
      warning_devices: 1,
      unknown_devices: 0,
      active_incidents: 2,
      critical_incidents: 1,
      daily_incidents: 3,
      agents_total: 6,
      agents_active: 5,
      agents_offline: 1,
      devices_by_building: [
        {
          building_id: 1,
          building_name: 'Asosiy Bino',
          total_devices: 10,
          online: 8,
          offline: 1,
          warning: 1,
        },
      ],
      telemetry_summary: {
        avg_cpu_percent: 24.5,
        avg_ram_percent: 68.2,
        avg_disk_percent: 45.0,
        total_telemetry_records: 120,
      },
      active_outages_count: 1,
      pending_remediations_count: 0,
      verified_remediations_count: 4,
      failed_remediations_count: 0,
      recent_recoveries_count: 4,
    });

    render(<SysAdminDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('15 Total')).toBeInTheDocument();
      expect(screen.getByText('24.5%')).toBeInTheDocument(); // avg cpu
      expect(screen.getByText('68.2%')).toBeInTheDocument(); // avg ram
      expect(screen.getByText('Asosiy Bino')).toBeInTheDocument();
    });
  });

  it('renders Executive Dashboard without misleading SLA numbers when unavailable', async () => {
    vi.mocked(dashboardApi.getExecutiveDashboard).mockResolvedValueOnce({
      timestamp: '2026-11-14T06:00:00Z',
      organization_id: 1,
      sla_target_percent: 99.5,
      contractual_sla_uptime_percent: null,
      contractual_sla_status: 'unavailable',
      contractual_sla_achievement_percent: null,
      probe_success_ratio_percent: 94.2,
      probe_success_status: 'operational',
      current_device_snapshot_percent: 88.0,
      infrastructure_availability_percent: 88.0,
      mttd_minutes: 2.5,
      mttr_minutes: 14.0,
      mttd_status: 'optimal',
      mttr_status: 'optimal',
      total_incidents_period: 3,
      active_risk_level: 'low',
      incident_trends: [],
      top_risk_devices: [
        {
          device_id: 10,
          name: 'Core Switch Lab-1',
          hostname: 'sw-core-01',
          device_type: 'switch',
          ip_address: '192.168.10.1',
          incident_count: 2,
          consecutive_failures: 0,
          status: 'online',
        },
      ],
      business_impact_summary: {},
    });

    render(<ExecutiveDashboardPage />);

    await waitFor(() => {
      // Contractual SLA Target displayed
      expect(screen.getByText('99.50%')).toBeInTheDocument();
      // Measured contractual SLA rendered as unavailable, not fabricated
      expect(screen.getAllByText(/Mavjud emas/i).length).toBeGreaterThan(0);
      // Probe ratio displayed
      expect(screen.getByText('94.2%')).toBeInTheDocument();
      // Risk device rendered
      expect(screen.getByText('Core Switch Lab-1')).toBeInTheDocument();
    });
  });

  it('renders Employee Dashboard with personal tickets and software requests', async () => {
    vi.mocked(dashboardApi.getEmployeeDashboard).mockResolvedValueOnce({
      timestamp: '2026-11-14T06:00:00Z',
      user_id: 5,
      user_name: 'Muhammadyusuf Usmonov',
      open_tickets_count: 1,
      resolved_tickets_count: 4,
      recent_tickets: [
        {
          id: 101,
          title: 'Laboratoriya printeri ulanmayapti',
          priority: 'medium',
          status: 'in_progress',
          created_at: '2026-11-14T04:30:00Z',
        },
      ],
      pending_software_requests_count: 1,
      recent_software_requests: [
        {
          id: 50,
          software_name: 'Wireshark Network Analyzer',
          status: 'pending',
          created_at: '2026-11-14T05:00:00Z',
        },
      ],
    });

    render(<EmployeeDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Muhammadyusuf Usmonov/i)).toBeInTheDocument();
      expect(screen.getByText('Laboratoriya printeri ulanmayapti')).toBeInTheDocument();
      expect(screen.getByText('Wireshark Network Analyzer')).toBeInTheDocument();
    });
  });
});
