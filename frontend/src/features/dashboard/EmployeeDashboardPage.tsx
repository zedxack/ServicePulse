import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  LifeBuoy,
  Plus,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { dashboardApi } from '../../shared/api/dashboard';
import { EmployeeDashboardResponse } from '../../shared/types/dashboard';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';
import { EmptyState } from '../../shared/components/EmptyState';

export const EmployeeDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  let navigate: (to: string) => void = () => {};
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    navigate = useNavigate();
  } catch {
    // Fallback when rendered outside Router in isolated tests
  }
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
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <LoadingSkeleton height="h-8" width="w-64" />
          <LoadingSkeleton height="h-8" width="w-32" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <LoadingSkeleton height="h-32" />
          <LoadingSkeleton height="h-32" />
          <LoadingSkeleton height="h-32" />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <LoadingSkeleton height="h-64" />
          <LoadingSkeleton height="h-64" />
        </div>
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

  const getPriorityBadge = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical':
      case 'high':
        return <Badge variant="offline" size="sm">{priority}</Badge>;
      case 'medium':
        return <Badge variant="warning" size="sm">{priority}</Badge>;
      default:
        return <Badge variant="mono" size="sm">{priority}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'resolved':
      case 'approved':
        return <Badge variant="online" size="sm">{status}</Badge>;
      case 'open':
      case 'pending':
        return <Badge variant="warning" size="sm">{status}</Badge>;
      case 'rejected':
      case 'closed':
        return <Badge variant="mono" size="sm">{status}</Badge>;
      default:
        return <Badge variant="brand" size="sm">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome */}
      <div className="relative overflow-hidden rounded-2xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-6 shadow-xs">
        <div className="absolute right-0 top-0 -mt-6 -mr-6 h-36 w-36 rounded-full bg-brand-500/10 blur-2xl" />
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md border border-brand-500/20 bg-brand-500/10 p-1 text-brand-600 dark:text-brand-400">
                <Sparkles className="h-4 w-4" />
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
                {t('employee.welcome')}, {data.user_name}
              </h1>
            </div>
            <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">
              {t('employee.subtitle')}
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Plus className="h-3.5 w-3.5" />}
              onClick={() => navigate('/tickets')}
            >
              Report Issue
            </Button>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Download className="h-3.5 w-3.5" />}
              onClick={() => navigate('/software')}
            >
              Request Software
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchData}
              leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            >
              {t('dashboard.refresh')}
            </Button>
          </div>
        </div>
      </div>

      {/* Row 1: Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Open Tickets */}
        <MetricCard
          title={t('employee.openTickets')}
          value={data.open_tickets_count}
          subtitle="Tickets awaiting technical staff response"
          icon={<Clock className="h-4 w-4" />}
          accentColor={data.open_tickets_count > 0 ? 'amber' : 'brand'}
        />

        {/* Resolved Tickets */}
        <MetricCard
          title={t('employee.resolvedTickets')}
          value={data.resolved_tickets_count}
          subtitle="Successfully closed service requests"
          icon={<CheckCircle2 className="h-4 w-4" />}
          accentColor="emerald"
        />

        {/* Pending Software Requests */}
        <MetricCard
          title={t('employee.pendingSoftware')}
          value={data.pending_software_requests_count}
          subtitle="Awaiting administrative approval"
          icon={<Download className="h-4 w-4" />}
          accentColor="purple"
        />
      </div>

      {/* Row 2: Recent Tickets & Software Requests */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Tickets Panel */}
        <div className="rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-xs transition-colors overflow-hidden">
          <div className="flex items-center justify-between border-b border-surface-200 dark:border-surface-800 px-6 py-4">
            <div className="flex items-center gap-2">
              <LifeBuoy className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              <h2 className="text-sm font-bold text-surface-900 dark:text-white">
                {t('employee.recentTickets')}
              </h2>
            </div>
            <button
              onClick={() => navigate('/tickets')}
              className="text-xs font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300"
            >
              View all
            </button>
          </div>
          <div className="overflow-x-auto">
            {data.recent_tickets && data.recent_tickets.length > 0 ? (
              <table className="w-full text-left text-xs">
                <thead className="border-b border-surface-100 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 font-semibold text-surface-600 dark:text-surface-400">
                  <tr>
                    <th className="px-6 py-3.5">{t('common.title')}</th>
                    <th className="px-6 py-3.5">{t('common.priority')}</th>
                    <th className="px-6 py-3.5">{t('common.status')}</th>
                    <th className="px-6 py-3.5">{t('common.date')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 dark:divide-surface-800/80 text-surface-700 dark:text-surface-300">
                  {data.recent_tickets.map((tkt) => (
                    <tr
                      key={tkt.id}
                      onClick={() => navigate(`/tickets?id=${tkt.id}`)}
                      className="cursor-pointer hover:bg-surface-50/70 dark:hover:bg-surface-800/40 transition-colors"
                    >
                      <td className="px-6 py-3.5 font-medium text-surface-900 dark:text-white">
                        {tkt.title}
                      </td>
                      <td className="px-6 py-3.5">{getPriorityBadge(tkt.priority)}</td>
                      <td className="px-6 py-3.5">{getStatusBadge(tkt.status)}</td>
                      <td className="px-6 py-3.5 font-mono text-surface-400">
                        {new Date(tkt.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8">
                <EmptyState
                  icon={<LifeBuoy className="h-6 w-6" />}
                  title={t('employee.noTickets')}
                  description="You have not submitted any support tickets yet."
                  action={
                    <Button size="sm" onClick={() => navigate('/tickets')}>
                      Create Ticket
                    </Button>
                  }
                />
              </div>
            )}
          </div>
        </div>

        {/* Recent Software Requests Panel */}
        <div className="rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-xs transition-colors overflow-hidden">
          <div className="flex items-center justify-between border-b border-surface-200 dark:border-surface-800 px-6 py-4">
            <div className="flex items-center gap-2">
              <Download className="h-4 w-4 text-purple-600 dark:text-purple-400" />
              <h2 className="text-sm font-bold text-surface-900 dark:text-white">
                {t('employee.recentSoftware')}
              </h2>
            </div>
            <button
              onClick={() => navigate('/software')}
              className="text-xs font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300"
            >
              View all
            </button>
          </div>
          <div className="overflow-x-auto">
            {data.recent_software_requests && data.recent_software_requests.length > 0 ? (
              <table className="w-full text-left text-xs">
                <thead className="border-b border-surface-100 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 font-semibold text-surface-600 dark:text-surface-400">
                  <tr>
                    <th className="px-6 py-3.5">{t('common.software')}</th>
                    <th className="px-6 py-3.5">{t('common.status')}</th>
                    <th className="px-6 py-3.5">{t('common.date')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 dark:divide-surface-800/80 text-surface-700 dark:text-surface-300">
                  {data.recent_software_requests.map((sw) => (
                    <tr
                      key={sw.id}
                      onClick={() => navigate('/software')}
                      className="cursor-pointer hover:bg-surface-50/70 dark:hover:bg-surface-800/40 transition-colors"
                    >
                      <td className="px-6 py-3.5 font-semibold text-surface-900 dark:text-white">
                        {sw.software_name}
                      </td>
                      <td className="px-6 py-3.5">{getStatusBadge(sw.status)}</td>
                      <td className="px-6 py-3.5 font-mono text-surface-400">
                        {new Date(sw.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8">
                <EmptyState
                  icon={<Download className="h-6 w-6" />}
                  title={t('employee.noSoftware')}
                  description="You have no pending or approved software catalog requests."
                  action={
                    <Button size="sm" variant="secondary" onClick={() => navigate('/software')}>
                      Browse Catalog
                    </Button>
                  }
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
