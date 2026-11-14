/**
 * ServicePulse - Analytics & SLA Performance Dashboard
 * Author: Muhammadyusuf Usmonov
 * Academic Purpose: AT-Servis BMI
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-primary-600" />
            {t('analytics.title', 'Analytics & SLA Performance')}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t(
              'analytics.subtitle',
              'Duration-based uptime calculations, maintenance window exclusions, and reliability trends'
            )}
          </p>
        </div>

        {/* Period Selector & Refresh */}
        <div className="flex items-center gap-3">
          <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 p-1 bg-white dark:bg-gray-800 text-xs font-medium">
            {[7, 30, 90].map((days) => (
              <button
                key={days}
                onClick={() => setPeriodDays(days)}
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  periodDays === days
                    ? 'bg-primary-600 text-white font-semibold'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {days} {t('analytics.days', 'Days')}
              </button>
            ))}
          </div>

          <button
            onClick={handleRefresh}
            className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
            title={t('common.refresh', 'Refresh')}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Insufficient Data Warning Banner */}
      {sla?.status === 'insufficient_data' && (
        <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex items-start gap-3">
          <HelpCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-200">
              {t('analytics.insufficient_data_title', 'Insufficient Historical Probe Data')}
            </h4>
            <p className="text-xs text-amber-800 dark:text-amber-300 mt-0.5">
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
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm md:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
              {t('analytics.measured_uptime', 'Measured Uptime')} ({periodDays}d)
            </span>
            {sla?.status === 'met' && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {t('analytics.sla_met', 'SLA Target Met')}
              </span>
            )}
            {sla?.status === 'breached' && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300">
                <XCircle className="w-3.5 h-3.5" />
                {t('analytics.sla_breached', 'SLA Breached')}
              </span>
            )}
            {sla?.status === 'insufficient_data' && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                <AlertTriangle className="w-3.5 h-3.5" />
                {t('analytics.insufficient_data_short', 'Insufficient Data')}
              </span>
            )}
          </div>

          <div className="flex items-baseline gap-3 my-2">
            <span className="text-4xl font-extrabold text-gray-900 dark:text-white">
              {isSlaLoading
                ? '...'
                : sla?.measured_uptime_percent !== null && sla?.measured_uptime_percent !== undefined
                ? `${sla.measured_uptime_percent.toFixed(2)}%`
                : '—'}
            </span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {t('analytics.target', 'Target')}: <strong className="text-gray-700 dark:text-gray-300">{sla?.target_percent ?? 99.9}%</strong>
            </span>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            {t(
              'analytics.uptime_formula',
              'Uptime % = (Eligible Duration − Unplanned Downtime) / Eligible Duration'
            )}
          </p>
        </div>

        {/* MTTR */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 text-sm">
            <span>{t('analytics.mttr', 'Mean Time To Resolve')}</span>
            <Clock className="w-4 h-4 text-blue-500" />
          </div>
          <div className="my-2">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {isSlaLoading
                ? '...'
                : sla?.mttr_seconds !== null && sla?.mttr_seconds !== undefined
                ? formatDuration(sla.mttr_seconds)
                : '—'}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('analytics.mttr_desc', 'Avg recovery duration')}
            </div>
          </div>
          <div className="text-[11px] text-gray-400">
            {sla?.active_outages_count ?? 0} {t('analytics.active_outages', 'active outages')}
          </div>
        </div>

        {/* MTTD */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400 text-sm">
            <span>{t('analytics.mttd', 'Mean Time To Detect')}</span>
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="my-2">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {isSlaLoading
                ? '...'
                : sla?.mttd_seconds !== null && sla?.mttd_seconds !== undefined
                ? `${sla.mttd_seconds}s`
                : '—'}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('analytics.mttd_desc', 'Detection probe window')}
            </div>
          </div>
          <div className="text-[11px] text-gray-400">
            {sla?.monitored_devices_count ?? 0} {t('analytics.devices_analyzed', 'devices evaluated')}
          </div>
        </div>
      </div>

      {/* Measurement Durations Breakdown */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4">
          {t('analytics.duration_breakdown', 'Measurement Duration Breakdown')}
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div className="p-3 bg-gray-50 dark:bg-gray-750 rounded-lg">
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('analytics.total_duration', 'Total Time Window')}
            </div>
            <div className="text-lg font-bold text-gray-900 dark:text-white mt-1">
              {formatDuration(sla?.total_measurement_seconds ?? 0)}
            </div>
          </div>

          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <div className="text-xs text-blue-700 dark:text-blue-300">
              {t('analytics.eligible_duration', 'Eligible Window')}
            </div>
            <div className="text-lg font-bold text-blue-900 dark:text-blue-200 mt-1">
              {formatDuration(sla?.eligible_measurement_seconds ?? 0)}
            </div>
          </div>

          <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
            <div className="text-xs text-amber-700 dark:text-amber-300">
              {t('analytics.maintenance_duration', 'Planned Maintenance')}
            </div>
            <div className="text-lg font-bold text-amber-900 dark:text-amber-200 mt-1">
              {formatDuration(sla?.planned_maintenance_seconds ?? 0)}
            </div>
          </div>

          <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
            <div className="text-xs text-red-700 dark:text-red-300">
              {t('analytics.unplanned_downtime', 'Unplanned Downtime')}
            </div>
            <div className="text-lg font-bold text-red-900 dark:text-red-200 mt-1">
              {formatDuration(sla?.unplanned_downtime_seconds ?? 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Daily Availability Trend (Visual Bar Chart) */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">
              {t('analytics.daily_availability', 'Daily Availability Timeline')}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {t('analytics.sla_threshold_note', 'Target: 99.9% uptime per measurement interval')}
            </p>
          </div>
          <span className="text-xs text-gray-500">
            {availability?.points.length ?? 0} {t('analytics.days_recorded', 'days recorded')}
          </span>
        </div>

        {isAvailLoading ? (
          <div className="py-12 text-center text-gray-500">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-primary-500" />
            {t('common.loading', 'Loading availability timeline...')}
          </div>
        ) : availability?.points.length === 0 ? (
          <div className="py-12 text-center text-gray-400">
            {t('analytics.no_trend_data', 'No availability records in this time frame.')}
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
                    <div className="hidden group-hover:block absolute bottom-full mb-2 bg-gray-900 text-white text-[11px] rounded px-2 py-1 shadow-lg whitespace-nowrap z-20 pointer-events-none">
                      <div className="font-semibold">{pt.date}</div>
                      <div>
                        {t('analytics.uptime', 'Uptime')}:{' '}
                        {uptime !== null ? `${uptime.toFixed(2)}%` : 'Insufficient Data'}
                      </div>
                      <div>
                        {t('analytics.outages', 'Outages')}: {pt.outage_count}
                      </div>
                    </div>

                    <div
                      className={`w-full rounded-t transition-all duration-300 ${
                        uptime === null
                          ? 'bg-gray-300 dark:bg-gray-700'
                          : isCompliant
                          ? 'bg-green-500 hover:bg-green-600'
                          : 'bg-red-500 hover:bg-red-600'
                      }`}
                      style={{ height: `${heightPercent}%` }}
                    />
                    <span className="text-[10px] text-gray-400 mt-1 truncate max-w-[32px]">
                      {pt.date.slice(5)}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-gray-100 dark:border-gray-700">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded bg-green-500 inline-block" />
                  {t('analytics.compliant', 'SLA Compliant (≥ 99.9%)')}
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded bg-red-500 inline-block" />
                  {t('analytics.breached_bar', 'Breached (< 99.9%)')}
                </span>
              </div>
              <span>{t('analytics.zero_fabricated', 'Zero synthetic data')}</span>
            </div>
          </div>
        )}
      </div>

      {/* Incident Distribution Trend */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">
              {t('analytics.incident_distribution', 'Daily Incident Occurrences')}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {t('analytics.total_recorded_incidents', 'Total incidents in window')}:{' '}
              <strong>{incidentTrends?.total_incidents ?? 0}</strong>
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
              {t('incidents.critical', 'Critical')}
            </span>
            <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              {t('incidents.warning', 'Warning')}
            </span>
            <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
              {t('incidents.info', 'Info')}
            </span>
          </div>
        </div>

        {isIncidentsLoading ? (
          <div className="py-12 text-center text-gray-500">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-primary-500" />
            {t('common.loading', 'Loading incident trends...')}
          </div>
        ) : incidentTrends?.points.length === 0 ? (
          <div className="py-12 text-center text-gray-400">
            {t('analytics.no_incidents_recorded', 'No incidents recorded in this window.')}
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
                  <div className="hidden group-hover:block absolute bottom-full mb-2 bg-gray-900 text-white text-[11px] rounded px-2 py-1 shadow-lg whitespace-nowrap z-20 pointer-events-none">
                    <div className="font-semibold">{pt.date}</div>
                    <div>
                      {t('analytics.total', 'Total')}: {pt.total}
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
                        className="bg-red-500"
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
                        className="bg-blue-500"
                        style={{ height: `${(pt.info / pt.total) * 100}%` }}
                      />
                    )}
                  </div>
                  <span className="text-[10px] text-gray-400 mt-1 truncate max-w-[32px]">
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
