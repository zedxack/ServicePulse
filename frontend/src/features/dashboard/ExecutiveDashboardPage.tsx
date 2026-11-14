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
          <h1 className="text-2xl font-bold tracking-tight text-surface-900">{t('executive.title')}</h1>
          <p className="text-xs text-surface-500">{t('executive.subtitle')}</p>
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

      {/* Row 1: SLA Target & Measured Availability */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Contractual SLA Target */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('executive.slaTarget')}</span>
            <Award className="h-4 w-4 text-brand-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.sla_target_percent.toFixed(2)}%</div>
          <div className="mt-1 text-[11px] text-surface-500">Agreed target threshold</div>
        </div>

        {/* Contractual SLA (Duration-based) */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('executive.contractualSla')}</span>
            <Shield className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="mt-2 text-xl font-bold text-surface-600">
            {data.contractual_sla_uptime_percent != null
              ? `${data.contractual_sla_uptime_percent.toFixed(2)}%`
              : t('dashboard.unavailable')}
          </div>
          <div className="mt-1 flex items-center gap-1 text-[11px] text-amber-600">
            <Info className="h-3 w-3 shrink-0" />
            <span className="truncate">{t('executive.slaStatusNotice')}</span>
          </div>
        </div>

        {/* Probe Success Ratio */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('executive.probeSuccessRatio')}</span>
            <Gauge className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">
            {data.probe_success_ratio_percent != null
              ? `${data.probe_success_ratio_percent.toFixed(1)}%`
              : t('dashboard.insufficientData')}
          </div>
          <div className="mt-1 text-[11px] text-surface-500">Discrete network check ratio</div>
        </div>

        {/* Current Snapshot Availability */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('executive.infrastructureAvailability')}</span>
            <CheckCircle className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">
            {data.current_device_snapshot_percent.toFixed(1)}%
          </div>
          <div className="mt-1 text-[11px] text-surface-500">Live online device proportion</div>
        </div>
      </div>

      {/* Row 2: MTTD, MTTR & Risk */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('executive.mttd')}</span>
            <Clock className="h-4 w-4 text-brand-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">
            {data.mttd_minutes != null ? `${data.mttd_minutes.toFixed(1)} ${t('executive.minutes')}` : data.mttd_status}
          </div>
          <div className="mt-1 text-[11px] text-surface-500">Average detection latency</div>
        </div>

        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('executive.mttr')}</span>
            <Zap className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">
            {data.mttr_minutes != null ? `${data.mttr_minutes.toFixed(1)} ${t('executive.minutes')}` : data.mttr_status}
          </div>
          <div className="mt-1 text-[11px] text-surface-500">Average recovery resolution time</div>
        </div>

        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('executive.activeRisk')}</span>
            <AlertCircle className={`h-4 w-4 ${data.active_risk_level === 'low' ? 'text-emerald-600' : 'text-amber-600'}`} />
          </div>
          <div className="mt-2 text-2xl font-bold capitalize text-surface-900">{data.active_risk_level}</div>
          <div className="mt-1 text-[11px] text-surface-500">
            {data.total_incidents_period} incidents evaluated
          </div>
        </div>
      </div>

      {/* Row 3: Top Risk Devices */}
      <div className="rounded-xl border border-surface-200 bg-white shadow-xs">
        <div className="border-b border-surface-200 px-6 py-4">
          <h2 className="text-sm font-bold text-surface-900">{t('executive.topRiskDevices')}</h2>
        </div>
        <div className="overflow-x-auto">
          {data.top_risk_devices && data.top_risk_devices.length > 0 ? (
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600">
                <tr>
                  <th className="px-6 py-3">Device</th>
                  <th className="px-6 py-3">Hostname</th>
                  <th className="px-6 py-3">IP Address</th>
                  <th className="px-6 py-3">Type</th>
                  <th className="px-6 py-3">Incidents</th>
                  <th className="px-6 py-3">{t('common.status')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 text-surface-700">
                {data.top_risk_devices.map((dev) => (
                  <tr key={dev.device_id} className="hover:bg-surface-50/50">
                    <td className="px-6 py-3 font-semibold text-surface-900">{dev.name}</td>
                    <td className="px-6 py-3 font-mono text-surface-600">{dev.hostname}</td>
                    <td className="px-6 py-3 font-mono text-surface-600">{dev.ip_address}</td>
                    <td className="px-6 py-3 capitalize text-surface-500">{dev.device_type}</td>
                    <td className="px-6 py-3 font-bold text-amber-600">{dev.incident_count}</td>
                    <td className="px-6 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        dev.status === 'online' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                      }`}>
                        {dev.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-xs text-surface-400">
              {t('executive.noRiskDevices')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
