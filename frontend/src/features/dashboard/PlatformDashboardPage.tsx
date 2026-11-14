import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  Building,
  CheckCircle2,
  RefreshCw,
  Server,
  ShieldAlert,
} from 'lucide-react';
import { dashboardApi } from '../../shared/api/dashboard';
import { PlatformDashboardResponse } from '../../shared/types/dashboard';

export const PlatformDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<PlatformDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await dashboardApi.getPlatformDashboard();
      setData(resp);
    } catch {
      setError(t('dashboard.errorLoading'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600"></div>
          <span className="text-xs font-medium text-surface-500">{t('dashboard.loading')}</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-red-500" />
        <p className="mt-2 text-sm font-semibold text-red-800">{error || t('dashboard.errorLoading')}</p>
        <button
          onClick={fetchData}
          className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-700"
        >
          {t('dashboard.refresh')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-surface-900">{t('platform.title')}</h1>
          <p className="text-xs text-surface-500">{t('platform.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-surface-400">
            {t('dashboard.lastUpdated')}: {new Date(data.timestamp).toLocaleTimeString()}
          </span>
          <button
            onClick={fetchData}
            className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-medium text-surface-700 shadow-xs hover:bg-surface-50 transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>{t('dashboard.refresh')}</span>
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Organizations */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('platform.totalOrgs')}</span>
            <div className="rounded-lg bg-brand-50 p-2 text-brand-600">
              <Building className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.total_organizations}</div>
          <div className="mt-1 flex items-center gap-2 text-[11px] text-surface-500">
            <span className="text-emerald-600 font-semibold">{data.active_organizations} {t('platform.activeOrgs').toLowerCase()}</span>
            <span>&bull;</span>
            <span className="text-surface-400">{data.inactive_organizations} {t('platform.inactiveOrgs').toLowerCase()}</span>
          </div>
        </div>

        {/* Platform Devices */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('platform.platformDevices')}</span>
            <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
              <Server className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.total_platform_devices}</div>
          <div className="mt-1 text-[11px] text-surface-500">
            {data.total_platform_agents} {t('platform.platformAgents').toLowerCase()}
          </div>
        </div>

        {/* Global Active Incidents */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('platform.globalIncidents')}</span>
            <div className={`rounded-lg p-2 ${data.global_active_incidents > 0 ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'}`}>
              <ShieldAlert className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.global_active_incidents}</div>
          <div className="mt-1 text-[11px] text-surface-500">
            {data.global_active_incidents === 0 ? 'No active outages' : 'Attention required'}
          </div>
        </div>

        {/* System Health */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('platform.systemHealth')}</span>
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            <span className="text-lg font-bold capitalize text-emerald-700">{data.platform_health_status}</span>
          </div>
          <div className="mt-1 text-[11px] text-surface-500">
            {data.total_platform_users} {t('platform.platformUsers').toLowerCase()}
          </div>
        </div>
      </div>

      {/* Global Audit Trail Table */}
      <div className="rounded-xl border border-surface-200 bg-white shadow-xs">
        <div className="border-b border-surface-200 px-6 py-4">
          <h2 className="text-sm font-bold text-surface-900">{t('platform.recentAudits')}</h2>
        </div>
        <div className="overflow-x-auto">
          {data.recent_global_audits && data.recent_global_audits.length > 0 ? (
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600">
                <tr>
                  <th className="px-6 py-3">{t('common.action')}</th>
                  <th className="px-6 py-3">{t('common.resource')}</th>
                  <th className="px-6 py-3">ID</th>
                  <th className="px-6 py-3">{t('common.status')}</th>
                  <th className="px-6 py-3">{t('common.date')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 text-surface-700">
                {data.recent_global_audits.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-50/50">
                    <td className="px-6 py-3 font-mono font-medium text-surface-900">{item.action}</td>
                    <td className="px-6 py-3 capitalize text-surface-600">{item.target_resource}</td>
                    <td className="px-6 py-3 font-mono text-surface-500">{item.target_id || '-'}</td>
                    <td className="px-6 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        item.status === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-surface-500">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-xs text-surface-400">
              {t('platform.noAudits')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
