import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  RefreshCw,
} from 'lucide-react';
import { dashboardApi } from '../../shared/api/dashboard';
import { EmployeeDashboardResponse } from '../../shared/types/dashboard';

export const EmployeeDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [data, setData] = useState<EmployeeDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await dashboardApi.getEmployeeDashboard();
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
          <h1 className="text-2xl font-bold tracking-tight text-surface-900">
            {t('employee.welcome')}, {data.user_name}
          </h1>
          <p className="text-xs text-surface-500">{t('employee.subtitle')}</p>
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

      {/* Row 1: Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Open Tickets */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('employee.openTickets')}</span>
            <div className="rounded-lg bg-amber-50 p-2 text-amber-600">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.open_tickets_count}</div>
          <div className="mt-1 text-[11px] text-surface-500">Awaiting technical support</div>
        </div>

        {/* Resolved Tickets */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('employee.resolvedTickets')}</span>
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.resolved_tickets_count}</div>
          <div className="mt-1 text-[11px] text-surface-500">Successfully closed issues</div>
        </div>

        {/* Pending Software Requests */}
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500">{t('employee.pendingSoftware')}</span>
            <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
              <Download className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold text-surface-900">{data.pending_software_requests_count}</div>
          <div className="mt-1 text-[11px] text-surface-500">Awaiting IT approval</div>
        </div>
      </div>

      {/* Row 2: Recent Tickets & Software Requests */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Tickets Panel */}
        <div className="rounded-xl border border-surface-200 bg-white shadow-xs">
          <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4">
            <h2 className="text-sm font-bold text-surface-900">{t('employee.recentTickets')}</h2>
          </div>
          <div className="overflow-x-auto">
            {data.recent_tickets && data.recent_tickets.length > 0 ? (
              <table className="w-full text-left text-xs">
                <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600">
                  <tr>
                    <th className="px-6 py-3">{t('common.title')}</th>
                    <th className="px-6 py-3">{t('common.priority')}</th>
                    <th className="px-6 py-3">{t('common.status')}</th>
                    <th className="px-6 py-3">{t('common.date')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 text-surface-700">
                  {data.recent_tickets.map((tkt) => (
                    <tr key={tkt.id} className="hover:bg-surface-50/50">
                      <td className="px-6 py-3 font-medium text-surface-900">{tkt.title}</td>
                      <td className="px-6 py-3 capitalize text-surface-500">{tkt.priority}</td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          tkt.status === 'resolved' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                        }`}>
                          {tkt.status}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-surface-400">
                        {new Date(tkt.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-xs text-surface-400">
                {t('employee.noTickets')}
              </div>
            )}
          </div>
        </div>

        {/* Recent Software Requests Panel */}
        <div className="rounded-xl border border-surface-200 bg-white shadow-xs">
          <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4">
            <h2 className="text-sm font-bold text-surface-900">{t('employee.recentSoftware')}</h2>
          </div>
          <div className="overflow-x-auto">
            {data.recent_software_requests && data.recent_software_requests.length > 0 ? (
              <table className="w-full text-left text-xs">
                <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600">
                  <tr>
                    <th className="px-6 py-3">{t('common.software')}</th>
                    <th className="px-6 py-3">{t('common.status')}</th>
                    <th className="px-6 py-3">{t('common.date')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 text-surface-700">
                  {data.recent_software_requests.map((sw) => (
                    <tr key={sw.id} className="hover:bg-surface-50/50">
                      <td className="px-6 py-3 font-semibold text-surface-900">{sw.software_name}</td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          sw.status === 'approved' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                        }`}>
                          {sw.status}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-surface-400">
                        {new Date(sw.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-xs text-surface-400">
                {t('employee.noSoftware')}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
