import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  AlertTriangle,
  Award,
  CheckCircle,
  Clock,
  Gauge,
  Info,
  RefreshCw,
  Shield,
  Zap,
} from 'lucide-react';
import { dashboardApi } from '../../shared/api/dashboard';
import { CEODashboardResponse } from '../../shared/types/dashboard';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';
import { EmptyState } from '../../shared/components/EmptyState';
import { PulseIndicator } from '../../shared/components/PulseIndicator';

export const ExecutiveDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<CEODashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await dashboardApi.getExecutiveDashboard();
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

  const getRiskBadgeVariant = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'low':
        return 'online';
      case 'medium':
        return 'warning';
      case 'high':
      case 'critical':
        return 'offline';
      default:
        return 'mono';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top NOC & Executive Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('executive.title')}
            </h1>
            <span className="telemetry-pill font-mono">
              <span className="status-dot status-dot-online" />
              SLA INTELLIGENCE
            </span>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400 mt-0.5">
            {t('executive.subtitle')}
          </p>
        </div>

        {/* Status Indicators & Refresh */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="hidden sm:inline-flex items-center gap-2 rounded-lg border border-surface-200 dark:border-white/10 bg-surface-50 dark:bg-surface-900/80 px-3 py-1.5 text-xs font-mono text-surface-600 dark:text-surface-300 shadow-2xs">
            <Shield className="h-3.5 w-3.5 text-brand-500" />
            <span>CONTRACT: ACTIVE</span>
            <span className="text-surface-300 dark:text-surface-700">&bull;</span>
            <span className="text-emerald-600 dark:text-emerald-400 font-semibold">MTTR: OPTIMAL</span>
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

      {/* Row 1: SLA Target & Measured Availability */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Contractual SLA Target */}
        <MetricCard
          title={t('executive.slaTarget')}
          value={`${data.sla_target_percent.toFixed(2)}%`}
          subtitle="Contractual minimum uptime commitment"
          icon={<Award className="h-4 w-4" />}
          accentColor="brand"
          className="noc-card"
        />

        {/* Contractual SLA (Duration-based) */}
        <MetricCard
          title={t('executive.contractualSla')}
          value={
            data.contractual_sla_uptime_percent != null
              ? `${data.contractual_sla_uptime_percent.toFixed(2)}%`
              : t('dashboard.unavailable')
          }
          subtitle="Duration-weighted operational uptime"
          icon={<Shield className="h-4 w-4" />}
          accentColor="purple"
          className="noc-card"
        >
          <div className="mt-3 flex items-center gap-1.5 border-t border-surface-100 dark:border-white/5 pt-2 text-[11px] text-amber-600 dark:text-amber-400">
            <Info className="h-3 w-3 shrink-0" />
            <span className="truncate">{t('executive.slaStatusNotice')}</span>
          </div>
        </MetricCard>

        {/* Probe Success Ratio */}
        <MetricCard
          title={t('executive.probeSuccessRatio')}
          value={
            data.probe_success_ratio_percent != null
              ? `${data.probe_success_ratio_percent.toFixed(1)}%`
              : t('dashboard.insufficientData')
          }
          subtitle="Discrete network health check ratio"
          icon={<Gauge className="h-4 w-4" />}
          accentColor="emerald"
          className="noc-card"
        />

        {/* Current Snapshot Availability */}
        <MetricCard
          title={t('executive.infrastructureAvailability')}
          value={`${data.current_device_snapshot_percent.toFixed(1)}%`}
          subtitle="Real-time proportion of active nodes"
          icon={<CheckCircle className="h-4 w-4" />}
          accentColor="cyan"
          className="noc-card"
        />
      </div>

      {/* Row 2: MTTD, MTTR & Risk */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* MTTD */}
        <div className="noc-card p-5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
              {t('executive.mttd')}
            </span>
            <div className="rounded-lg bg-brand-500/10 p-1.5 text-brand-600 dark:text-brand-400">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-mono font-bold text-surface-900 dark:text-white">
            {data.mttd_minutes != null
              ? `${data.mttd_minutes.toFixed(1)} ${t('executive.minutes')}`
              : data.mttd_status}
          </div>
          <p className="mt-1 text-xs text-surface-400 font-mono">Mean time to detect service degradation</p>
        </div>

        {/* MTTR */}
        <div className="noc-card p-5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
              {t('executive.mttr')}
            </span>
            <div className="rounded-lg bg-indigo-500/10 p-1.5 text-indigo-600 dark:text-indigo-400">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-mono font-bold text-surface-900 dark:text-white">
            {data.mttr_minutes != null
              ? `${data.mttr_minutes.toFixed(1)} ${t('executive.minutes')}`
              : data.mttr_status}
          </div>
          <p className="mt-1 text-xs text-surface-400 font-mono">Mean time to resolve and recover incidents</p>
        </div>

        {/* Active Risk */}
        <div className="noc-card p-5 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
              {t('executive.activeRisk')}
            </span>
            <div className="rounded-lg bg-amber-500/10 p-1.5 text-amber-600 dark:text-amber-400">
              <AlertCircle className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 flex items-center gap-3">
            <Badge variant={getRiskBadgeVariant(data.active_risk_level)} size="md">
              {data.active_risk_level.toUpperCase()} RISK
            </Badge>
          </div>
          <p className="mt-2 text-xs text-surface-400 font-mono">
            {data.total_incidents_period} incidents evaluated across active SLA period
          </p>
        </div>
      </div>

      {/* Row 3: Top Risk Infrastructure */}
      <div className="noc-panel overflow-hidden transition-colors">
        <div className="flex items-center justify-between border-b border-surface-200 dark:border-white/10 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-rose-500/10 p-2 text-rose-600 dark:text-rose-400">
              <AlertTriangle className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-surface-900 dark:text-white">
                {t('executive.topRiskDevices')}
              </h2>
              <p className="text-xs text-surface-500 dark:text-surface-400">
                Infrastructure assets accumulating repeat service interruptions
              </p>
            </div>
          </div>
          <span className="text-xs font-mono text-surface-400 bg-surface-100 dark:bg-surface-800 px-2.5 py-1 rounded-md">
            {data.top_risk_devices?.length || 0} flagged
          </span>
        </div>
        <div className="overflow-x-auto">
          {data.top_risk_devices && data.top_risk_devices.length > 0 ? (
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-100 dark:border-white/5 bg-surface-50 dark:bg-surface-950/60 font-semibold text-surface-600 dark:text-surface-400">
                <tr>
                  <th className="px-6 py-3.5">Device Name</th>
                  <th className="px-6 py-3.5">Hostname</th>
                  <th className="px-6 py-3.5">IP Address</th>
                  <th className="px-6 py-3.5">Asset Type</th>
                  <th className="px-6 py-3.5">Incident Load</th>
                  <th className="px-6 py-3.5">{t('common.status')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-white/5 text-surface-700 dark:text-surface-300">
                {data.top_risk_devices.map((dev) => (
                  <tr
                    key={dev.device_id}
                    className="hover:bg-surface-50/70 dark:hover:bg-surface-800/40 transition-colors"
                  >
                    <td className="px-6 py-3.5 font-semibold text-surface-900 dark:text-white">
                      {dev.name}
                    </td>
                    <td className="px-6 py-3.5 font-mono text-surface-600 dark:text-surface-400">
                      {dev.hostname || '—'}
                    </td>
                    <td className="px-6 py-3.5 font-mono text-surface-800 dark:text-surface-200 font-medium">
                      {dev.ip_address || '—'}
                    </td>
                    <td className="px-6 py-3.5 capitalize text-surface-600 dark:text-surface-300">
                      {dev.device_type}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="font-mono font-bold text-amber-600 dark:text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                        {dev.incident_count}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 font-mono">
                      <Badge
                        variant={dev.status === 'online' ? 'online' : dev.status === 'warning' ? 'warning' : 'offline'}
                        size="sm"
                      >
                        {dev.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8">
              <EmptyState
                icon={<Shield className="h-6 w-6" />}
                title={t('executive.noRiskDevices')}
                description="All monitored devices are currently operating within nominal SLA reliability thresholds."
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
