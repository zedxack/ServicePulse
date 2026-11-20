import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  Building2,
  HardDrive,
  History,
  RefreshCw,
  ShieldAlert,
  Users,
} from 'lucide-react';
import { dashboardApi } from '../../shared/api/dashboard';
import { CompanyDashboardResponse } from '../../shared/types/dashboard';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { PulseIndicator } from '../../shared/components/PulseIndicator';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';
import { EmptyState } from '../../shared/components/EmptyState';
import { UserAndInvitationManagementSection } from './UserAndInvitationManagementSection';

export const CompanyDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'overview' | 'users'>('overview');
  const [data, setData] = useState<CompanyDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await dashboardApi.getCompanyDashboard();
      setData(resp);
    } catch {
      setError(t('dashboard.errorLoading', 'Failed to load company telemetry'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 rounded bg-surface-200 dark:bg-surface-800 animate-pulse" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <LoadingSkeleton variant="card" count={4} />
        </div>
        <LoadingSkeleton variant="card" className="h-64" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center dark:border-red-900/50 dark:bg-red-950/40">
        <AlertTriangle className="mx-auto h-8 w-8 text-red-500" />
        <p className="mt-2 text-sm font-semibold text-red-800 dark:text-red-300">
          {error || t('dashboard.errorLoading', 'Failed to load dashboard')}
        </p>
        <button
          onClick={fetchData}
          className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-red-700"
        >
          {t('dashboard.refresh', 'Try Again')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('company.title', 'Company Administration Cockpit')}
            </h1>
            <Badge variant="brand" size="sm">{data.organization_name}</Badge>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400">
            {t('company.subtitle', 'Tenant resource quota, campus infrastructure and active incidents overview')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-surface-400 font-mono dark:text-surface-500">
            <PulseIndicator status="online" size="sm" />
            <span>{new Date(data.timestamp).toLocaleTimeString()}</span>
          </div>
          <button
            onClick={fetchData}
            className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-medium text-surface-700 shadow-xs hover:bg-surface-50 transition dark:border-white/10 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>{t('dashboard.refresh', 'Refresh')}</span>
          </button>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex rounded-xl border border-surface-200 bg-surface-100/80 p-1 text-xs font-semibold dark:border-white/10 dark:bg-surface-800/60 max-w-sm">
        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 transition-all ${
            activeTab === 'overview'
              ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
              : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
          }`}
        >
          <Building2 className="h-4 w-4" />
          <span>{t('company.overview', 'Overview & Quota')}</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('users')}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 transition-all ${
            activeTab === 'users'
              ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
              : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
          }`}
        >
          <Users className="h-4 w-4" />
          <span>{t('usersAndInvitations.tabLabel', 'Users & Invitations')}</span>
        </button>
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Metrics Grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title={t('company.totalUsers', 'Active Members')}
          value={data.total_users}
          subtitle="Provisioned employees & technicians"
          icon={Users}
          accent="brand"
        />

        <div className="group relative overflow-hidden rounded-xl border border-surface-200 bg-white p-5 shadow-xs transition-all duration-200 hover:border-surface-300 hover:shadow-sm dark:border-white/10 dark:bg-surface-900 dark:hover:border-white/20">
          <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-brand-500 to-indigo-500 opacity-80" />
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                {t('company.devicesCount', 'Device Quota')}
              </p>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="font-mono text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
                  {data.total_devices}
                </span>
                <span className="font-mono text-xs text-surface-500 dark:text-surface-400">
                  / {data.max_devices} max
                </span>
              </div>
              <div className="mt-2.5 h-1.5 w-full rounded-full bg-surface-100 overflow-hidden dark:bg-surface-800">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${
                    data.device_utilization_percent > 85 ? 'bg-amber-500' : 'bg-brand-600'
                  }`}
                  style={{ width: `${Math.min(data.device_utilization_percent, 100)}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-surface-500 dark:text-surface-400">
                <span className="font-mono font-semibold">{data.device_utilization_percent.toFixed(1)}%</span> {t('company.utilization', 'quota utilized')}
              </p>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-brand-200/50 bg-brand-50 text-brand-600 dark:border-white/5 dark:bg-brand-950/50 dark:text-brand-400">
              <HardDrive className="h-5 w-5" />
            </div>
          </div>
        </div>

        <MetricCard
          title={t('company.buildingsCount', 'Campus Locations')}
          value={data.total_buildings}
          subtitle="Monitored physical facilities"
          icon={Building2}
          accent="purple"
        />

        <MetricCard
          title={t('company.activeIncidents', 'Active Incidents')}
          value={data.active_incidents}
          subtitle={data.active_incidents === 0 ? 'All services operational' : 'Active remediation in progress'}
          icon={ShieldAlert}
          accent={data.active_incidents > 0 ? 'critical' : 'online'}
        />
      </div>

      {/* Organization Audit Trail Table */}
      <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs dark:border-white/10 dark:bg-surface-900">
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-white/10">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            <h2 className="text-sm font-bold text-surface-900 dark:text-white">
              {t('company.recentAudits', 'Organization Activity Ledger')}
            </h2>
          </div>
          <span className="text-[11px] font-mono text-surface-400 dark:text-surface-500">
            Tenant Operational Records
          </span>
        </div>

        <div className="overflow-x-auto">
          {data.recent_org_audits && data.recent_org_audits.length > 0 ? (
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600 dark:border-white/5 dark:bg-surface-800/60 dark:text-surface-300">
                <tr>
                  <th className="px-6 py-3">{t('common.action', 'Action')}</th>
                  <th className="px-6 py-3">{t('common.resource', 'Target Resource')}</th>
                  <th className="px-6 py-3">Resource ID</th>
                  <th className="px-6 py-3">{t('common.status', 'Status')}</th>
                  <th className="px-6 py-3">{t('common.date', 'Timestamp')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 text-surface-700 dark:divide-white/5 dark:text-surface-300">
                {data.recent_org_audits.map((item) => (
                  <tr key={item.id} className="transition-colors hover:bg-surface-50/80 dark:hover:bg-surface-800/40">
                    <td className="px-6 py-3.5 font-mono text-xs font-semibold text-surface-900 dark:text-white">
                      {item.action}
                    </td>
                    <td className="px-6 py-3.5 font-medium text-surface-600 dark:text-surface-300 capitalize">
                      {item.target_resource}
                    </td>
                    <td className="px-6 py-3.5 font-mono text-surface-500 dark:text-surface-400">
                      {item.target_id ? `#${item.target_id}` : '—'}
                    </td>
                    <td className="px-6 py-3.5">
                      <Badge
                        variant={item.status === 'success' ? 'online' : 'offline'}
                        size="xs"
                        dot={true}
                      >
                        {item.status}
                      </Badge>
                    </td>
                    <td className="px-6 py-3.5 font-mono text-xs text-surface-500 dark:text-surface-400">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState
              icon={Building2}
              title={t('company.noAudits', 'No recent organization activity')}
              description="Administrative and membership actions for your company will be cataloged here."
              className="m-6"
            />
          )}
        </div>
      </div>
    </div>
    )}

    {activeTab === 'users' && (
      <UserAndInvitationManagementSection
        scope="company"
        currentOrganizationId={data.organization_id}
        currentOrganizationName={data.organization_name}
      />
    )}
  </div>
);
};
