/**
 * ServicePulse - Alert Center Frontend Tests
 * Author: Muhammadyusuf Usmonov
 *  */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AlertCenterPage } from '../features/alerts/AlertCenterPage';
import * as AlertsApi from '../shared/api/alerts';
import * as AuthContextModule from '../features/auth/AuthContext';
import '../i18n/config';

vi.mock('../shared/api/alerts', () => ({
  getAlerts: vi.fn(),
  getUnreadAlertCount: vi.fn(),
  markAlertRead: vi.fn(),
  markAllAlertsRead: vi.fn(),
}));

describe('AlertCenterPage Component (STEP 5.3.3)', () => {
  let queryClient: QueryClient;

  const mockAlerts = {
    total: 2,
    unread_count: 1,
    items: [
      {
        id: 501,
        organization_id: 1,
        user_id: null,
        target_role: null,
        title: 'Core Switch Offline',
        message: 'Device Core Switch failed 3 consecutive ICMP ping probes.',
        severity: 'critical' as const,
        category: 'device' as const,
        fingerprint: 'dev_offline_10',
        is_read: false,
        is_dismissed: false,
        read_at: null,
        created_at: '2026-11-14T09:45:00Z',
        data: { device_id: 10, ip_address: '192.168.10.1' },
      },
      {
        id: 502,
        organization_id: 1,
        user_id: null,
        target_role: null,
        title: 'High CPU Incident Created',
        message: 'Incident #102 opened for server high CPU utilization.',
        severity: 'warning' as const,
        category: 'incident' as const,
        fingerprint: 'inc_opened_102',
        is_read: true,
        is_dismissed: false,
        read_at: '2026-11-14T09:50:00Z',
        created_at: '2026-11-14T09:40:00Z',
        data: { incident_id: 102 },
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
        email: 'itadmin@servicepulse.uz',
        full_name: 'IT Admin Officer',
        organization_id: 1,
        is_active: true,
        is_superuser: false,
        created_at: '2026-01-01T00:00:00Z',
        roles: [{ id: 3, name: 'it_admin' }],
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

    vi.mocked(AlertsApi.getAlerts).mockResolvedValue(mockAlerts);
    vi.mocked(AlertsApi.markAlertRead).mockResolvedValue({
      ...mockAlerts.items[0],
      is_read: true,
      read_at: new Date().toISOString(),
    });
    vi.mocked(AlertsApi.markAllAlertsRead).mockResolvedValue({ updated_count: 1 });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AlertCenterPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders Alert Center title and unread counter badge', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Core Switch Offline')).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Alert & Notification Center|Xabarnomalar va Ogohlantirishlar Markazi|Центр оповещений/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/unread|o'qilmagan|непрочитано/i)).toBeInTheDocument();
  });

  it('renders individual alert items with severity and contextual links', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Core Switch Offline')).toBeInTheDocument();
    });

    expect(screen.getByText('High CPU Incident Created')).toBeInTheDocument();
    expect(screen.getByText(/View Device #10|Qurilmani ko'rish #10|Открыть устройство #10/i)).toBeInTheDocument();
    expect(screen.getByText(/View Incident #102|Hodisani ko'rish #102|Открыть инцидент #102/i)).toBeInTheDocument();
  });

  it('triggers mark single alert read mutation on click', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Core Switch Offline')).toBeInTheDocument();
    });

    const markReadBtn = screen.getByTitle(/Mark as read|O'qilgan deb belgilash|Отметить прочитанным/i);
    fireEvent.click(markReadBtn);

    await waitFor(() => {
      expect(AlertsApi.markAlertRead).toHaveBeenCalledWith(501);
    });
  });

  it('triggers mark all alerts read mutation on click', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Mark all as read|Barchasini o'qilgan deb belgilash|Отметить все как прочитанные/i)).toBeInTheDocument();
    });

    const markAllBtn = screen.getByText(/Mark all as read|Barchasini o'qilgan deb belgilash|Отметить все как прочитанные/i);
    fireEvent.click(markAllBtn);

    await waitFor(() => {
      expect(AlertsApi.markAllAlertsRead).toHaveBeenCalled();
    });
  });

  it('toggles unread only filter', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Core Switch Offline')).toBeInTheDocument();
    });

    const toggleBtn = screen.getByText(/Showing: All Statuses|Ko'rsatilmoqda: Barcha Holatlar|Показано: все статусы/i);
    fireEvent.click(toggleBtn);

    expect(AlertsApi.getAlerts).toHaveBeenCalledWith(
      expect.objectContaining({ unread_only: true })
    );
  });
});
