/**
 * ServicePulse - Analytics & SLA Frontend Tests
 * Author: Muhammadyusuf Usmonov
 * Academic Purpose: AT-Servis BMI
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnalyticsPage } from '../features/analytics/AnalyticsPage';
import * as AnalyticsApi from '../shared/api/analytics';
import * as AuthContextModule from '../features/auth/AuthContext';
import '../i18n/config';

vi.mock('../shared/api/analytics', () => ({
  getSLAOverview: vi.fn(),
  getAvailabilityTrend: vi.fn(),
  getIncidentTrends: vi.fn(),
}));

describe('AnalyticsPage Component (STEP 5.3.2)', () => {
  let queryClient: QueryClient;

  const mockSLAOverviewMet = {
    period_days: 30,
    target_percent: 99.9,
    measured_uptime_percent: 99.95,
    meets_target: true,
    total_measurement_seconds: 2592000,
    eligible_measurement_seconds: 2580000,
    unmonitored_seconds: 0,
    planned_maintenance_seconds: 12000,
    unplanned_downtime_seconds: 1290,
    monitored_devices_count: 5,
    active_outages_count: 0,
    mttr_seconds: 320,
    mttd_seconds: 45,
    period_start: '2026-10-15T00:00:00Z',
    period_end: '2026-11-14T00:00:00Z',
    status: 'met' as const,
  };

  const mockAvailabilityTrend = {
    period_days: 30,
    target_percent: 99.9,
    overall_uptime_percent: 99.95,
    points: [
      {
        date: '2026-11-13',
        uptime_percent: 100.0,
        eligible_seconds: 86400,
        downtime_seconds: 0,
        outage_count: 0,
        meets_sla: true,
      },
      {
        date: '2026-11-14',
        uptime_percent: 99.92,
        eligible_seconds: 86400,
        downtime_seconds: 69,
        outage_count: 1,
        meets_sla: true,
      },
    ],
  };

  const mockIncidentTrends = {
    period_days: 30,
    total_incidents: 4,
    mttr_minutes: 5.3,
    points: [
      {
        date: '2026-11-13',
        total: 1,
        critical: 0,
        warning: 1,
        info: 0,
      },
      {
        date: '2026-11-14',
        total: 3,
        critical: 1,
        warning: 2,
        info: 0,
      },
    ],
  };

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
        email: 'executive@servicepulse.uz',
        full_name: 'Executive Officer',
        organization_id: 1,
        is_active: true,
        is_superuser: false,
        created_at: '2026-01-01T00:00:00Z',
        roles: [{ id: 4, name: 'executive' }],
        primary_dashboard: 'executive',
      },
      hasRole: () => true,
      hasAnyRole: () => true,
      isLoading: false,
      isAuthenticated: true,
      token: 'mock_token',
      login: vi.fn(),
      logout: vi.fn(),
    });

    vi.mocked(AnalyticsApi.getSLAOverview).mockResolvedValue(mockSLAOverviewMet);
    vi.mocked(AnalyticsApi.getAvailabilityTrend).mockResolvedValue(mockAvailabilityTrend);
    vi.mocked(AnalyticsApi.getIncidentTrends).mockResolvedValue(mockIncidentTrends);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AnalyticsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders SLA Overview cards with measured uptime and Met badge', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/99.95%/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/SLA Target Met|SLA Talabi Bajarildi|Цель SLA достигнута/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Target|Maqsad|Цель/i)[0]).toBeInTheDocument();
  });

  it('displays MTTR and MTTD metrics accurately', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('5m')).toBeInTheDocument(); // 320s = 5m
    });

    expect(screen.getByText('45s')).toBeInTheDocument();
  });

  it('displays duration breakdown categories', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Eligible Window|Mumkin Bo'lgan Vaqt|Допустимое время/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Planned Maintenance|Rejalashtirilgan Xizmat|Плановое обслуживание/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Unplanned Downtime|Rejasiz To'xtalish|Внеплановый простой/i)[0]).toBeInTheDocument();
  });

  it('renders insufficient data warning when data is insufficient', async () => {
    vi.mocked(AnalyticsApi.getSLAOverview).mockResolvedValue({
      ...mockSLAOverviewMet,
      status: 'insufficient_data',
      measured_uptime_percent: null,
    });

    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByText(/Insufficient Historical Probe Data|Tarixiy Kuzatuv Ma'lumotlari Yetarli Emas|Недостаточно исторических данных/i)
      ).toBeInTheDocument();
    });
  });

  it('changes period when clicking 7 Days or 90 Days', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/99.95%/i)).toBeInTheDocument();
    });

    const sevenDaysBtn = screen.getByText(/7 Days|7 Kun|7 Дней/i);
    fireEvent.click(sevenDaysBtn);

    expect(AnalyticsApi.getSLAOverview).toHaveBeenCalledWith(7);
  });
});
