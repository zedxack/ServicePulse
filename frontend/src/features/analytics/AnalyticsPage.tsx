/**
 * ServicePulse - Analytics & SLA Performance Dashboard
 * Author: Muhammadyusuf Usmonov
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  HelpCircle,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import {
  getAvailabilityTrend,
  getIncidentTrends,
  getSLAOverview,
} from '../../shared/api/analytics';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { EmptyState } from '../../shared/components/EmptyState';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';

export const AnalyticsPage: React.FC = () => {
  const { t } = useTranslation();
  const [periodDays, setPeriodDays] = useState<number>(30);

  const {
    data: sla,
    isLoading: isSlaLoading,
    refetch: refetchSla,
  } = useQuery({
    queryKey: ['sla-overview', periodDays],
    queryFn: () => getSLAOverview(periodDays),
  });

  const {
    data: availability,
    isLoading: isAvailLoading,
    refetch: refetchAvail,
  } = useQuery({
    queryKey: ['availability-trend', periodDays],
    queryFn: () => getAvailabilityTrend(periodDays),
  });

  const {
    data: incidentTrends,
    isLoading: isIncidentsLoading,
    refetch: refetchIncidents,
  } = useQuery({
    queryKey: ['incident-trends', periodDays],
    queryFn: () => getIncidentTrends(periodDays),
  });

  const handleRefresh = () => {
    refetchSla();
    refetchAvail();
    refetchIncidents();
  };

  const formatDuration = (seconds: number) => {
    if (seconds <= 0) return '0m';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hrs > 0) {
      return `${hrs}h ${mins}m`;
    }
    return `${mins}m`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <BarChart3 className="h-6 w-6 text-brand-600 dark:text-brand-400" />
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('analytics.title', 'Analytics & SLA Performance')}
            </h1>
            <span className="telemetry-pill font-mono">
              <span className="status-dot status-dot-online" />
              CONTRACTUAL RELIABILITY
            </span>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400 mt-0.5">
            {t(
              'analytics.subtitle',
              'Duration-based uptime calculations, maintenance window exclusions, and reliability trends'
            )}
          </p>
        </div>

        {/* Period Selector & Refresh */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="inline-flex rounded-lg border border-surface-200 dark:border-white/10 bg-surface-50 dark:bg-surface-950/60 p-1 text-xs font-semibold">
            {[7, 30, 90].map((days) => (
              <button
                key={days}
                onClick={() => setPeriodDays(days)}
                className={`rounded-md px-3 py-1.5 transition-colors font-mono ${
                  periodDays === days
                    ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs font-bold'
                    : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white'
                }`}
              >
                {days} {t('analytics.days', 'Days')}
              </button>
            ))}
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleRefresh}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            {t('common.refresh', 'Refresh')}
          </Button>
        </div>
      </div>

      {/* Insufficient Data Warning Banner */}
      {sla?.status === 'insufficient_data' && (
        <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 flex items-start gap-3">
          <HelpCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-200">
              {t('analytics.insufficient_data_title', 'Insufficient Historical Probe Data')}
            </h4>
            <p className="text-xs text-amber-800 dark:text-amber-300/90 mt-0.5">
              {t(
                'analytics.insufficient_data_desc',
                'ServicePulse strictly calculates uptime from verified probe observations and outage intervals without synthetic padding. A minimum of 10 observations is required to declare uptime compliance.'
              )}
            </p>
          </div>
        </div>
      )}

      {/* SLA Overview Banner & KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Measured Uptime */}
        <div className="noc-card p-5 transition-colors md:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
              {t('analytics.measured_uptime', 'Measured Uptime')} ({periodDays}d)
            </span>
            {sla?.status === 'met' && (
              <Badge variant="online" size="sm">
                <CheckCircle2 className="w-3 h-3" />
                {t('analytics.sla_met', 'SLA Target Met')}
              </Badge>
            )}
            {sla?.status === 'breached' && (
              <Badge variant="offline" size="sm">
                <XCircle className="w-3 h-3" />
                {t('analytics.sla_breached', 'SLA Breached')}
              </Badge>
            )}
            {sla?.status === 'insufficient_data' && (
              <Badge variant="warning" size="sm">
                <AlertTriangle className="w-3 h-3" />
                {t('analytics.insufficient_data_short', 'Insufficient Data')}
              </Badge>
            )}
          </div>

          <div className="flex items-baseline gap-3 my-2">
            <span className="font-mono text-4xl font-extrabold text-surface-900 dark:text-white">
              {isSlaLoading
                ? '...'
                : sla?.measured_uptime_percent !== null && sla?.measured_uptime_percent !== undefined
                ? `${sla.measured_uptime_percent.toFixed(2)}%`
                : '—'}
            </span>
            <span className="text-xs text-surface-500 dark:text-surface-400">
              {t('analytics.target', 'Target')}:{' '}
              <strong className="text-surface-800 dark:text-surface-200 font-mono">
                {sla?.target_percent ?? 99.9}%
              </strong>
            </span>
          </div>

          <p className="text-[11px] font-mono text-surface-400 dark:text-surface-500">
            {t(
              'analytics.uptime_formula',
              'Uptime % = (Eligible Duration − Unplanned Downtime) / Eligible Duration'
            )}
          </p>
        </div>

        {/* MTTR */}
        <MetricCard
          title={t('analytics.mttr', 'Mean Time To Resolve')}
          value={
            isSlaLoading
              ? '...'
              : sla?.mttr_seconds !== null && sla?.mttr_seconds !== undefined
              ? formatDuration(sla.mttr_seconds)
              : '—'
          }
          subtitle={`${sla?.active_outages_count ?? 0} active outages`}
          icon={<Clock className="w-4 h-4" />}
          accentColor="brand"
          className="noc-card"
        />

        {/* MTTD */}
        <MetricCard
          title={t('analytics.mttd', 'Mean Time To Detect')}
          value={
            isSlaLoading
              ? '...'
              : sla?.mttd_seconds !== null && sla?.mttd_seconds !== undefined
              ? `${sla.mttd_seconds}s`
              : '—'
          }
          subtitle={`${sla?.monitored_devices_count ?? 0} devices evaluated`}
          icon={<ShieldCheck className="w-4 h-4" />}
          accentColor="emerald"
          className="noc-card"
        />
      </div>

      {/* Measurement Durations Breakdown */}
      <div className="noc-panel p-5 transition-colors">
        <h3 className="text-sm font-bold text-surface-900 dark:text-white mb-4">
          {t('analytics.duration_breakdown', 'Measurement Duration Breakdown')}
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center font-mono">
          <div className="p-3.5 bg-surface-50 dark:bg-surface-800/50 rounded-lg border border-surface-100 dark:border-white/5">
            <div className="text-xs text-surface-500 dark:text-surface-400 font-sans">
              {t('analytics.total_duration', 'Total Time Window')}
            </div>
            <div className="text-lg font-bold text-surface-900 dark:text-white mt-1">
              {formatDuration(sla?.total_measurement_seconds ?? 0)}
            </div>
          </div>

          <div className="p-3.5 bg-brand-500/10 rounded-lg border border-brand-500/20">
            <div className="text-xs text-brand-700 dark:text-brand-300 font-sans">
              {t('analytics.eligible_duration', 'Eligible Window')}
            </div>
            <div className="text-lg font-bold text-brand-900 dark:text-brand-200 mt-1">
              {formatDuration(sla?.eligible_measurement_seconds ?? 0)}
            </div>
          </div>

          <div className="p-3.5 bg-amber-500/10 rounded-lg border border-amber-500/20">
            <div className="text-xs text-amber-700 dark:text-amber-300 font-sans">
              {t('analytics.maintenance_duration', 'Planned Maintenance')}
            </div>
            <div className="text-lg font-bold text-amber-900 dark:text-amber-200 mt-1">
              {formatDuration(sla?.planned_maintenance_seconds ?? 0)}
            </div>
          </div>

          <div className="p-3.5 bg-rose-500/10 rounded-lg border border-rose-500/20">
            <div className="text-xs text-rose-700 dark:text-rose-300 font-sans">
              {t('analytics.unplanned_downtime', 'Unplanned Downtime')}
            </div>
            <div className="text-lg font-bold text-rose-900 dark:text-rose-200 mt-1">
              {formatDuration(sla?.unplanned_downtime_seconds ?? 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Daily Availability Trend (Visual Bar Chart) */}
      <div className="noc-panel p-5 transition-colors">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-surface-900 dark:text-white">
              {t('analytics.daily_availability', 'Daily Availability Timeline')}
            </h3>
            <p className="text-xs text-surface-500 dark:text-surface-400">
              {t('analytics.sla_threshold_note', 'Target: 99.9% uptime per measurement interval')}
            </p>
          </div>
          <span className="text-xs font-mono text-surface-400 bg-surface-100 dark:bg-surface-800 px-2.5 py-1 rounded-md">
            {availability?.points.length ?? 0} {t('analytics.days_recorded', 'days recorded')}
          </span>
        </div>

        {isAvailLoading ? (
          <div className="py-12">
            <LoadingSkeleton height="h-44" />
          </div>
        ) : availability?.points.length === 0 ? (
          <div className="py-12">
            <EmptyState
              icon={<BarChart3 className="h-8 w-8" />}
              title="No Availability Records"
              description={t('analytics.no_trend_data', 'No availability records in this time frame.')}
            />
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-end gap-1.5 h-44 pt-6 pb-2 overflow-x-auto">
              {availability?.points.map((pt) => {
                const uptime = pt.uptime_percent;
                const heightPercent =
                  uptime !== null ? Math.max(10, Math.min(uptime, 100)) : 5;
                const isCompliant = pt.meets_sla;

                return (
                  <div
                    key={pt.date}
                    className="flex-1 min-w-[28px] max-w-[42px] flex flex-col items-center h-full justify-end group relative"
                  >
                    {/* Tooltip on hover */}
                    <div className="hidden group-hover:block absolute bottom-full mb-2 bg-surface-900 dark:bg-surface-800 text-white text-[11px] rounded-lg px-2.5 py-1.5 shadow-xl whitespace-nowrap z-20 pointer-events-none border border-surface-700">
                      <div className="font-semibold font-mono">{pt.date}</div>
                      <div>
                        {t('analytics.uptime', 'Uptime')}:{' '}
                        <span className="font-mono font-bold">
                          {uptime !== null ? `${uptime.toFixed(2)}%` : 'Insufficient Data'}
                        </span>
                      </div>
                      <div>
                        {t('analytics.outages', 'Outages')}: {pt.outage_count}
                      </div>
                    </div>

                    <div
                      className={`w-full rounded-t transition-all duration-300 ${
                        uptime === null
                          ? 'bg-surface-300 dark:bg-surface-700'
                          : isCompliant
                          ? 'bg-emerald-500 hover:bg-emerald-600'
                          : 'bg-rose-500 hover:bg-rose-600'
                      }`}
                      style={{ height: `${heightPercent}%` }}
                    />
                    <span className="text-[10px] font-mono text-surface-400 mt-1 truncate max-w-[32px]">
                      {pt.date.slice(5)}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center justify-between text-xs text-surface-400 pt-2 border-t border-surface-100 dark:border-white/5">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-xs bg-emerald-500 inline-block" />
                  {t('analytics.compliant', 'SLA Compliant (≥ 99.9%)')}
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-xs bg-rose-500 inline-block" />
                  {t('analytics.breached_bar', 'Breached (< 99.9%)')}
                </span>
              </div>
              <span className="font-mono text-[11px]">{t('analytics.zero_fabricated', 'Zero synthetic data')}</span>
            </div>
          </div>
        )}
      </div>

      {/* Incident Distribution Trend */}
      <div className="noc-panel p-5 transition-colors">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-surface-900 dark:text-white">
              {t('analytics.incident_distribution', 'Daily Incident Occurrences')}
            </h3>
            <p className="text-xs text-surface-500 dark:text-surface-400">
              {t('analytics.total_recorded_incidents', 'Total incidents in window')}:{' '}
              <strong className="text-surface-800 dark:text-surface-200 font-mono">
                {incidentTrends?.total_incidents ?? 0}
              </strong>
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400 font-medium">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
              {t('incidents.critical', 'Critical')}
            </span>
            <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              {t('incidents.warning', 'Warning')}
            </span>
            <span className="flex items-center gap-1 text-brand-600 dark:text-brand-400 font-medium">
              <span className="w-2.5 h-2.5 rounded-full bg-brand-500" />
              {t('incidents.info', 'Info')}
            </span>
          </div>
        </div>

        {isIncidentsLoading ? (
          <div className="py-12">
            <LoadingSkeleton height="h-36" />
          </div>
        ) : incidentTrends?.points.length === 0 ? (
          <div className="py-12">
            <EmptyState
              icon={<BarChart3 className="h-8 w-8" />}
              title="No Incident Occurrences"
              description={t('analytics.no_incidents_recorded', 'No incidents recorded in this window.')}
            />
          </div>
        ) : (
          <div className="flex items-end gap-1.5 h-36 pt-4 overflow-x-auto">
            {incidentTrends?.points.map((pt) => {
              const maxVal = Math.max(
                ...incidentTrends.points.map((p) => p.total),
                5
              );
              const heightPercent = Math.max(8, (pt.total / maxVal) * 100);

              return (
                <div
                  key={pt.date}
                  className="flex-1 min-w-[28px] max-w-[42px] flex flex-col items-center h-full justify-end group relative"
                >
                  <div className="hidden group-hover:block absolute bottom-full mb-2 bg-surface-900 dark:bg-surface-800 text-white text-[11px] rounded-lg px-2.5 py-1.5 shadow-xl whitespace-nowrap z-20 pointer-events-none border border-surface-700">
                    <div className="font-semibold font-mono">{pt.date}</div>
                    <div>
                      {t('analytics.total', 'Total')}: <span className="font-mono font-bold">{pt.total}</span>
                    </div>
                    <div>Critical: {pt.critical}</div>
                    <div>Warning: {pt.warning}</div>
                  </div>

                  <div
                    className="w-full flex flex-col-reverse rounded-t overflow-hidden"
                    style={{ height: `${heightPercent}%` }}
                  >
                    {pt.critical > 0 && (
                      <div
                        className="bg-rose-500"
                        style={{ height: `${(pt.critical / pt.total) * 100}%` }}
                      />
                    )}
                    {pt.warning > 0 && (
                      <div
                        className="bg-amber-500"
                        style={{ height: `${(pt.warning / pt.total) * 100}%` }}
                      />
                    )}
                    {pt.info > 0 && (
                      <div
                        className="bg-brand-500"
                        style={{ height: `${(pt.info / pt.total) * 100}%` }}
                      />
                    )}
                  </div>
                  <span className="text-[10px] font-mono text-surface-400 mt-1 truncate max-w-[32px]">
                    {pt.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
