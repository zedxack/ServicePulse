import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  AlertTriangle,
  Building2,
  CheckCircle2,
  History,
  RefreshCw,
  Server,
  Shield,
  ShieldAlert,
  Users,
} from 'lucide-react';
import { dashboardApi } from '../../shared/api/dashboard';
import { authApi } from '../../shared/api/auth';
import { PlatformDashboardResponse } from '../../shared/types/dashboard';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { PulseIndicator } from '../../shared/components/PulseIndicator';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';
import { EmptyState } from '../../shared/components/EmptyState';
import { OwnerAccessGovernanceSection } from './OwnerAccessGovernanceSection';
import { UserAndInvitationManagementSection } from './UserAndInvitationManagementSection';

export const PlatformDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();

  const tabParam = searchParams.get('tab');
  const [activeTab, setActiveTab] = useState<'telemetry' | 'users' | 'governance'>(
    tabParam === 'users' ? 'users' : tabParam === 'governance' ? 'governance' : 'telemetry'
  );

  const [data, setData] = useState<PlatformDashboardResponse | null>(null);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleTabChange = (tab: 'telemetry' | 'users' | 'governance') => {
    setActiveTab(tab);
    setSearchParams(tab === 'telemetry' ? {} : { tab });
  };

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [resp, stats] = await Promise.all([
        dashboardApi.getPlatformDashboard(),
        authApi.getAccessRequestStats().catch(() => ({ pending_count: 0, approved_count: 0, rejected_count: 0, total_count: 0 })),
      ]);
      setData(resp);
      setPendingCount(stats.pending_count);
    } catch {
      setError(t('dashboard.errorLoading', 'Failed to load platform telemetry'));
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
              {t('platform.title', 'Platform Super Admin Command Center')}
            </h1>
            <Badge variant="brand" size="xs">GLOBAL</Badge>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400">
            {t('platform.subtitle', 'Cross-tenant infrastructure orchestration, global telemetry and security governance')}
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

      {/* Main Tabs Navigation */}
      <div className="flex rounded-xl border border-surface-200 bg-surface-100/80 p-1 text-xs font-semibold dark:border-white/10 dark:bg-surface-800/60 max-w-xl">
        <button
          type="button"
          onClick={() => handleTabChange('telemetry')}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 transition-all ${
            activeTab === 'telemetry'
              ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
              : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
          }`}
        >
          <Activity className="h-4 w-4" />
          <span>System Intelligence</span>
        </button>
        <button
          type="button"
          onClick={() => handleTabChange('users')}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 transition-all ${
            activeTab === 'users'
              ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
              : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
          }`}
        >
          <Users className="h-4 w-4" />
          <span>{t('usersAndInvitations.tabLabel', 'Users & Invitations')}</span>
        </button>
        <button
          type="button"
          onClick={() => handleTabChange('governance')}
          className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 transition-all ${
            activeTab === 'governance'
              ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
              : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
          }`}
        >
          <Shield className="h-4 w-4" />
          <span>Owner Access Governance</span>
          {pendingCount > 0 && (
            <span className="rounded-full bg-amber-500 px-1.5 py-0.2 text-[10px] font-bold text-white">
              {pendingCount}
            </span>
          )}
        </button>
      </div>

      {/* Tab 1: System Intelligence & Global Audit Trail */}
      {activeTab === 'telemetry' && (
        <div className="space-y-6">
          {/* Metrics Grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title={t('platform.totalOrgs', 'Organizations')}
              value={data.total_organizations}
              subtitle={`${data.active_organizations} active • ${data.inactive_organizations} inactive`}
              icon={Building2}
              accent="brand"
            />

            <MetricCard
              title={t('platform.platformDevices', 'Managed Devices')}
              value={data.total_platform_devices}
              subtitle={`${data.total_platform_agents} active agent nodes`}
              icon={Server}
              accent="purple"
            />

            <MetricCard
              title={t('platform.globalIncidents', 'Active Incidents')}
              value={data.global_active_incidents}
              subtitle={data.global_active_incidents === 0 ? 'All organizations operational' : 'Critical triage required'}
              icon={ShieldAlert}
              accent={data.global_active_incidents > 0 ? 'critical' : 'online'}
            />

            <MetricCard
              title={t('platform.systemHealth', 'Platform Status')}
              value={data.platform_health_status.toUpperCase()}
              subtitle={`${data.total_platform_users} registered users`}
              icon={CheckCircle2}
              accent="online"
            />
          </div>

          {/* Global Audit Trail Table */}
          <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs dark:border-white/10 dark:bg-surface-900">
            <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-white/10">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                <h2 className="text-sm font-bold text-surface-900 dark:text-white">
                  {t('platform.recentAudits', 'Global Security Audit Trail')}
                </h2>
              </div>
              <span className="text-[11px] font-mono text-surface-400 dark:text-surface-500">
                Real-Time Tamper-Evident Ledger
              </span>
            </div>

            <div className="overflow-x-auto">
              {data.recent_global_audits && data.recent_global_audits.length > 0 ? (
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
                    {data.recent_global_audits.map((item) => (
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
                  icon={Activity}
                  title={t('platform.noAudits', 'No recent audit events')}
                  description="Platform administrative and security actions will be recorded in this tamper-evident ledger."
                  className="m-6"
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Users & Invitations Management */}
      {activeTab === 'users' && (
        <UserAndInvitationManagementSection scope="platform" />
      )}

      {/* Tab 3: Owner Access Governance Center */}
      {activeTab === 'governance' && (
        <OwnerAccessGovernanceSection />
      )}
    </div>
  );
};
