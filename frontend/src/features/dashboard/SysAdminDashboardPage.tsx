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
  Radio,
  Layers,
} from 'lucide-react';
import { dashboardApi } from '../../shared/api/dashboard';
import { SysAdminDashboardResponse } from '../../shared/types/dashboard';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';
import { EmptyState } from '../../shared/components/EmptyState';
import { PulseIndicator } from '../../shared/components/PulseIndicator';

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
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <LoadingSkeleton height="h-8" width="w-64" />
          <LoadingSkeleton height="h-8" width="w-32" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <LoadingSkeleton height="h-32" />
          <LoadingSkeleton height="h-32" />
          <LoadingSkeleton height="h-32" />
          <LoadingSkeleton height="h-32" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <LoadingSkeleton height="h-28" />
          <LoadingSkeleton height="h-28" />
          <LoadingSkeleton height="h-28" />
        </div>
        <LoadingSkeleton height="h-64" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/20 p-6 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-rose-500" />
        <p className="mt-2 text-sm font-semibold text-rose-800 dark:text-rose-300">
          {error || t('dashboard.errorLoading')}
        </p>
        <div className="mt-4 flex justify-center">
          <Button variant="danger" size="sm" onClick={fetchData}>
            {t('dashboard.refresh')}
          </Button>
        </div>
      </div>
    );
  }

  const getMeterColor = (val: number | null | undefined) => {
    if (val == null) return 'bg-surface-400';
    if (val >= 90) return 'bg-rose-500 dark:bg-rose-400';
    if (val >= 75) return 'bg-amber-500 dark:bg-amber-400';
    return 'bg-brand-500 dark:bg-brand-400';
  };

  const isFleetHealthy = data.offline_devices === 0 && data.critical_incidents === 0;

  return (
    <div className="space-y-6">
      {/* Top NOC Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('sysadmin.title')}
            </h1>
            <span className="telemetry-pill font-mono">
              <span className={`status-dot ${isFleetHealthy ? 'status-dot-online' : 'status-dot-critical'}`} />
              OPERATIONS COCKPIT
            </span>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400 mt-0.5">
            {t('sysadmin.subtitle')}
          </p>
        </div>

        {/* Action Controls & Telemetry Badges */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="hidden sm:inline-flex items-center gap-2 rounded-lg border border-surface-200 dark:border-white/10 bg-surface-50 dark:bg-surface-900/80 px-3 py-1.5 text-xs font-mono text-surface-600 dark:text-surface-300 shadow-2xs">
            <Radio className="h-3.5 w-3.5 text-brand-500 animate-pulse" />
            <span>INGESTION: ACTIVE</span>
            <span className="text-surface-300 dark:text-surface-700">&bull;</span>
            <span>POLL: 30s</span>
          </div>

          <div className="hidden items-center gap-1.5 text-xs text-surface-400 sm:flex font-mono">
            <PulseIndicator status="online" size="sm" />
            <span>
              {t('dashboard.lastUpdated')}: {new Date(data.timestamp).toLocaleTimeString()}
            </span>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={fetchData}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            {t('dashboard.refresh')}
          </Button>
        </div>
      </div>

      {/* Row 1: Fleet Health & Incidents */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Device Status */}
        <MetricCard
          title="Fleet Device Status"
          value={`${data.total_devices} Total`}
          subtitle="Registered Network & Agent Nodes"
          icon={<Server className="h-4 w-4" />}
          accentColor="brand"
          className="noc-card"
        >
          <div className="mt-3 flex items-center justify-between border-t border-surface-100 dark:border-white/5 pt-2.5 text-xs font-mono">
            <span className="flex items-center gap-1.5 font-medium text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" /> {data.online_devices}
            </span>
            <span className="flex items-center gap-1.5 font-medium text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5" /> {data.warning_devices}
            </span>
            <span className="flex items-center gap-1.5 font-medium text-rose-600 dark:text-rose-400">
              <XCircle className="h-3.5 w-3.5" /> {data.offline_devices}
            </span>
          </div>
        </MetricCard>

        {/* Active Incidents */}
        <MetricCard
          title={t('sysadmin.activeIncidents')}
          value={data.active_incidents}
          subtitle={`${data.critical_incidents} critical requiring triage`}
          icon={<AlertOctagon className="h-4 w-4" />}
          accentColor={data.critical_incidents > 0 ? 'rose' : data.active_incidents > 0 ? 'amber' : 'emerald'}
          className="noc-card"
        >
          <div className="mt-3 flex items-center justify-between border-t border-surface-100 dark:border-white/5 pt-2.5 text-xs">
            <Badge variant={data.critical_incidents > 0 ? 'offline' : 'mono'} size="sm">
              {data.critical_incidents} {t('sysadmin.criticalIncidents').toLowerCase()}
            </Badge>
            <span className="text-[11px] font-mono text-surface-500 dark:text-surface-400">
              {data.daily_incidents} today
            </span>
          </div>
        </MetricCard>

        {/* Windows Agents */}
        <MetricCard
          title="Agent Heartbeats"
          value={data.agents_total}
          subtitle={`${data.agents_active} streaming continuous telemetry`}
          icon={<Activity className="h-4 w-4" />}
          accentColor="purple"
          className="noc-card"
        >
          <div className="mt-3 flex items-center justify-between border-t border-surface-100 dark:border-white/5 pt-2.5 text-xs">
            <span className="flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400">
              <PulseIndicator status="online" size="sm" />
              {data.agents_active} {t('sysadmin.activeAgents').toLowerCase()}
            </span>
            <span className="text-surface-400 dark:text-surface-500 font-mono text-xs">
              {data.agents_offline} {t('sysadmin.offlineAgents').toLowerCase()}
            </span>
          </div>
        </MetricCard>

        {/* Automated Remediations */}
        <MetricCard
          title="Auto Remediations"
          value={data.verified_remediations_count}
          subtitle="Self-healing actions verified"
          icon={<Wrench className="h-4 w-4" />}
          accentColor="emerald"
          className="noc-card"
        >
          <div className="mt-3 flex items-center justify-between border-t border-surface-100 dark:border-white/5 pt-2.5 text-xs font-mono">
            <span className="text-amber-600 dark:text-amber-400 font-medium">
              {data.pending_remediations_count} pending
            </span>
            <span className="text-surface-300 dark:text-surface-600">&bull;</span>
            <span className="text-rose-600 dark:text-rose-400 font-medium">
              {data.failed_remediations_count} failed
            </span>
          </div>
        </MetricCard>
      </div>

      {/* Row 2: Live Telemetry Gauges */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* CPU */}
        <div className="noc-card p-5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
              {t('sysadmin.avgCpu')}
            </span>
            <div className="rounded-lg bg-brand-500/10 p-1.5 text-brand-600 dark:text-brand-400">
              <Cpu className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-mono text-2xl font-bold text-surface-900 dark:text-white">
              {data.telemetry_summary.avg_cpu_percent != null
                ? `${data.telemetry_summary.avg_cpu_percent.toFixed(1)}%`
                : t('dashboard.unavailable')}
            </span>
            <span className="text-[11px] font-mono text-surface-400">fleet average</span>
          </div>
          <div className="mt-3 h-2 w-full rounded-full bg-surface-100 dark:bg-surface-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${getMeterColor(
                data.telemetry_summary.avg_cpu_percent
              )}`}
              style={{ width: `${Math.min(data.telemetry_summary.avg_cpu_percent || 0, 100)}%` }}
            />
          </div>
        </div>

        {/* RAM */}
        <div className="noc-card p-5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
              {t('sysadmin.avgRam')}
            </span>
            <div className="rounded-lg bg-indigo-500/10 p-1.5 text-indigo-600 dark:text-indigo-400">
              <Database className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-mono text-2xl font-bold text-surface-900 dark:text-white">
              {data.telemetry_summary.avg_ram_percent != null
                ? `${data.telemetry_summary.avg_ram_percent.toFixed(1)}%`
                : t('dashboard.unavailable')}
            </span>
            <span className="text-[11px] font-mono text-surface-400">fleet average</span>
          </div>
          <div className="mt-3 h-2 w-full rounded-full bg-surface-100 dark:bg-surface-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${getMeterColor(
                data.telemetry_summary.avg_ram_percent
              )}`}
              style={{ width: `${Math.min(data.telemetry_summary.avg_ram_percent || 0, 100)}%` }}
            />
          </div>
        </div>

        {/* Disk */}
        <div className="noc-card p-5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
              {t('sysadmin.avgDisk')}
            </span>
            <div className="rounded-lg bg-slate-500/10 p-1.5 text-slate-600 dark:text-slate-400">
              <HardDrive className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-mono text-2xl font-bold text-surface-900 dark:text-white">
              {data.telemetry_summary.avg_disk_percent != null
                ? `${data.telemetry_summary.avg_disk_percent.toFixed(1)}%`
                : t('dashboard.unavailable')}
            </span>
            <span className="text-[11px] font-mono text-surface-400">storage consumed</span>
          </div>
          <div className="mt-3 h-2 w-full rounded-full bg-surface-100 dark:bg-surface-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${getMeterColor(
                data.telemetry_summary.avg_disk_percent
              )}`}
              style={{ width: `${Math.min(data.telemetry_summary.avg_disk_percent || 0, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Row 3: Building Breakdown Table */}
      <div className="noc-panel overflow-hidden transition-colors">
        <div className="flex items-center justify-between border-b border-surface-200 dark:border-white/10 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-brand-500/10 p-2 text-brand-600 dark:text-brand-400">
              <Layers className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-surface-900 dark:text-white">
                {t('sysadmin.buildingsBreakdown')}
              </h2>
              <p className="text-xs text-surface-500 dark:text-surface-400">
                Distribution of infrastructure health by facility and branch
              </p>
            </div>
          </div>
          <span className="text-xs font-mono text-surface-400 bg-surface-100 dark:bg-surface-800 px-2.5 py-1 rounded-md">
            {data.devices_by_building?.length || 0} locations
          </span>
        </div>
        <div className="overflow-x-auto">
          {data.devices_by_building && data.devices_by_building.length > 0 ? (
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-100 dark:border-white/5 bg-surface-50 dark:bg-surface-950/60 font-semibold text-surface-600 dark:text-surface-400">
                <tr>
                  <th className="px-6 py-3.5">Building Location</th>
                  <th className="px-6 py-3.5">Total Devices</th>
                  <th className="px-6 py-3.5 text-emerald-600 dark:text-emerald-400">Online</th>
                  <th className="px-6 py-3.5 text-amber-600 dark:text-amber-400">Warning</th>
                  <th className="px-6 py-3.5 text-rose-600 dark:text-rose-400">Offline</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-white/5 text-surface-700 dark:text-surface-300">
                {data.devices_by_building.map((b) => (
                  <tr
                    key={b.building_id}
                    className="hover:bg-surface-50/70 dark:hover:bg-surface-800/40 transition-colors"
                  >
                    <td className="px-6 py-3.5 font-medium text-surface-900 dark:text-white">
                      <div className="flex items-center gap-2">
                        <div className="rounded p-1 bg-surface-100 dark:bg-surface-800 text-surface-500">
                          <Building2 className="h-3.5 w-3.5" />
                        </div>
                        <span className="font-semibold">{b.building_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5 font-mono font-semibold text-surface-800 dark:text-surface-200">
                      {b.total_devices}
                    </td>
                    <td className="px-6 py-3.5 font-mono">
                      <Badge variant="online" size="sm">
                        {b.online}
                      </Badge>
                    </td>
                    <td className="px-6 py-3.5 font-mono">
                      <Badge variant={b.warning > 0 ? 'warning' : 'mono'} size="sm">
                        {b.warning}
                      </Badge>
                    </td>
                    <td className="px-6 py-3.5 font-mono">
                      <Badge variant={b.offline > 0 ? 'offline' : 'mono'} size="sm">
                        {b.offline}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8">
              <EmptyState
                icon={<Building2 className="h-6 w-6" />}
                title={t('sysadmin.noBuildingData')}
                description="No campus or building locations have been mapped to device inventory yet."
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
