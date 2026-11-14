import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  Building2,
  CheckCircle2,
  Cpu,
  Database,
  HardDrive,
  RefreshCw,
  Server,
  Wrench,
  XCircle,
} from 'lucide-react';
import { dashboardApi } from '../../shared/api/dashboard';
import { SysAdminDashboardResponse } from '../../shared/types/dashboard';

export const SysAdminDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<SysAdminDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await dashboardApi.getSysAdminDashboard();
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
          <h1 className="text-2xl font-bold tracking-tight text-surface-900">{t('sysadmin.title')}</h1>
          <p className="text-xs text-surface-500">{t('sysadmin.subtitle')}</p>
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

      {/* Row 1: Device States & Incidents */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Device Online/Offline/Warning */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">Device Status</span>
            <Server className="h-4 w-4 text-brand-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.total_devices} Total</div>
          <div className="mt-2 flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1 text-emerald-600 font-medium">
              <CheckCircle2 className="h-3 w-3" /> {data.online_devices}
            </span>
            <span className="flex items-center gap-1 text-red-600 font-medium">
              <XCircle className="h-3 w-3" /> {data.offline_devices}
            </span>
            <span className="flex items-center gap-1 text-amber-600 font-medium">
              <AlertTriangle className="h-3 w-3" /> {data.warning_devices}
            </span>
          </div>
        </div>

        {/* Incidents (Active, Critical, Daily) */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('sysadmin.activeIncidents')}</span>
            <AlertOctagon className="h-4 w-4 text-red-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.active_incidents}</div>
          <div className="mt-2 flex items-center gap-3 text-xs">
            <span className="text-red-700 font-medium">{data.critical_incidents} {t('sysadmin.criticalIncidents').toLowerCase()}</span>
            <span>&bull;</span>
            <span className="text-surface-500">{data.daily_incidents} {t('sysadmin.dailyIncidents').toLowerCase()}</span>
          </div>
        </div>

        {/* Windows Agents */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">Agent Heartbeats</span>
            <Activity className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.agents_total} Agents</div>
          <div className="mt-2 flex items-center gap-3 text-xs">
            <span className="text-emerald-600 font-medium">{data.agents_active} {t('sysadmin.activeAgents').toLowerCase()}</span>
            <span>&bull;</span>
            <span className="text-surface-400">{data.agents_offline} {t('sysadmin.offlineAgents').toLowerCase()}</span>
          </div>
        </div>

        {/* Automated Remediations */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">Auto Remediations</span>
            <Wrench className="h-4 w-4 text-amber-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-700">{data.verified_remediations_count} Resolved</div>
          <div className="mt-2 flex items-center gap-3 text-xs">
            <span className="text-amber-600 font-medium">{data.pending_remediations_count} pending</span>
            <span>&bull;</span>
            <span className="text-red-600 font-medium">{data.failed_remediations_count} failed</span>
          </div>
        </div>
      </div>

      {/* Row 2: Live Telemetry Gauges */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('sysadmin.avgCpu')}</span>
            <Cpu className="h-4 w-4 text-brand-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">
            {data.telemetry_summary.avg_cpu_percent != null
              ? `${data.telemetry_summary.avg_cpu_percent.toFixed(1)}%`
              : t('dashboard.unavailable')}
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-surface-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-brand-600"
              style={{ width: `${Math.min(data.telemetry_summary.avg_cpu_percent || 0, 100)}%` }}
            />
          </div>
        </div>

        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('sysadmin.avgRam')}</span>
            <Database className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">
            {data.telemetry_summary.avg_ram_percent != null
              ? `${data.telemetry_summary.avg_ram_percent.toFixed(1)}%`
              : t('dashboard.unavailable')}
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-surface-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-indigo-600"
              style={{ width: `${Math.min(data.telemetry_summary.avg_ram_percent || 0, 100)}%` }}
            />
          </div>
        </div>

        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('sysadmin.avgDisk')}</span>
            <HardDrive className="h-4 w-4 text-slate-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">
            {data.telemetry_summary.avg_disk_percent != null
              ? `${data.telemetry_summary.avg_disk_percent.toFixed(1)}%`
              : t('dashboard.unavailable')}
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-surface-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-slate-600"
              style={{ width: `${Math.min(data.telemetry_summary.avg_disk_percent || 0, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Row 3: Building Breakdown Table */}
      <div className="rounded-xl border border-surface-200 bg-white shadow-xs">
        <div className="border-b border-surface-200 px-6 py-4">
          <h2 className="text-sm font-bold text-surface-900">{t('sysadmin.buildingsBreakdown')}</h2>
        </div>
        <div className="overflow-x-auto">
          {data.devices_by_building && data.devices_by_building.length > 0 ? (
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600">
                <tr>
                  <th className="px-6 py-3">Building</th>
                  <th className="px-6 py-3">Total Devices</th>
                  <th className="px-6 py-3 text-emerald-600">Online</th>
                  <th className="px-6 py-3 text-red-600">Offline</th>
                  <th className="px-6 py-3 text-amber-600">Warning</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 text-surface-700">
                {data.devices_by_building.map((b) => (
                  <tr key={b.building_id} className="hover:bg-surface-50/50">
                    <td className="px-6 py-3 font-medium text-surface-900 flex items-center gap-2">
                      <Building2 className="h-3.5 w-3.5 text-surface-400" />
                      {b.building_name}
                    </td>
                    <td className="px-6 py-3 font-semibold text-surface-800">{b.total_devices}</td>
                    <td className="px-6 py-3 text-emerald-600 font-medium">{b.online}</td>
                    <td className="px-6 py-3 text-red-600 font-medium">{b.offline}</td>
                    <td className="px-6 py-3 text-amber-600 font-medium">{b.warning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-xs text-surface-400">
              {t('sysadmin.noBuildingData')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
