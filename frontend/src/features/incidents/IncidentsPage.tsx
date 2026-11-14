import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  ShieldAlert,
} from 'lucide-react';
import { incidentsApi } from '../../shared/api/incidents';
import { IncidentRead } from '../../shared/types/incident';
import { ResolveIncidentModal } from './ResolveIncidentModal';
import { useAuth } from '../auth/AuthContext';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { EmptyState } from '../../shared/components/EmptyState';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';

export const IncidentsPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasAnyRole } = useAuth();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [resolvingIncident, setResolvingIncident] = useState<IncidentRead | null>(null);

  const canRespond = hasAnyRole(['platform_super_admin', 'company_admin', 'it_admin', 'support', 'admin']);

  const {
    data: incidentData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['incidentsList', selectedSeverity, selectedStatus],
    queryFn: () =>
      incidentsApi.listIncidents({
        severity: selectedSeverity !== 'all' ? selectedSeverity : undefined,
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
        limit: 100,
      }),
  });

  const ackMutation = useMutation({
    mutationFn: (incidentId: number) =>
      incidentsApi.acknowledgeIncident(incidentId, { notes: 'Quick ack from list' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidentsList'] });
    },
  });

  const incidents = incidentData?.items || [];
  const filteredIncidents = incidents.filter((inc) => {
    const q = searchQuery.toLowerCase();
    return (
      inc.title.toLowerCase().includes(q) ||
      inc.description.toLowerCase().includes(q) ||
      inc.fingerprint.toLowerCase().includes(q)
    );
  });

  const criticalCount = incidents.filter((i) => i.severity === 'critical' && i.status !== 'resolved').length;
  const openCount = incidents.filter((i) => i.status === 'open').length;
  const resolvedCount = incidents.filter((i) => i.status === 'resolved').length;

  const getSeverityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return <Badge variant="offline" size="sm">{t('incidents.critical')}</Badge>;
      case 'warning':
        return <Badge variant="warning" size="sm">{t('incidents.warning')}</Badge>;
      default:
        return <Badge variant="info" size="sm">{t('incidents.info')}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open':
        return <Badge variant="offline" size="sm">{t('incidents.open')}</Badge>;
      case 'acknowledged':
        return <Badge variant="warning" size="sm">{t('incidents.acknowledged')}</Badge>;
      case 'in_progress':
        return <Badge variant="brand" size="sm">{t('incidents.inProgress')}</Badge>;
      case 'resolved':
        return <Badge variant="online" size="sm">{t('incidents.resolved')}</Badge>;
      default:
        return <Badge variant="mono" size="sm">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('incidents.title')}
            </h1>
            <span className="rounded-md border border-rose-500/20 bg-rose-500/10 px-2 py-0.5 text-[11px] font-semibold text-rose-600 dark:text-rose-400">
              Active Triage
            </span>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400">{t('incidents.subtitle')}</p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
          leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
        >
          {t('dashboard.refresh')}
        </Button>
      </div>

      {/* Counters */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          title="Total Incidents"
          value={isLoading ? '—' : incidentData?.total ?? 0}
          subtitle="All recorded incident records"
          icon={<AlertCircle className="h-4 w-4" />}
          accentColor="brand"
        />
        <MetricCard
          title="Critical Outages"
          value={isLoading ? '—' : criticalCount}
          subtitle="High-impact active alerts"
          icon={<AlertTriangle className="h-4 w-4" />}
          accentColor={criticalCount > 0 ? 'rose' : 'emerald'}
        />
        <MetricCard
          title="Open Incidents"
          value={isLoading ? '—' : openCount}
          subtitle="Awaiting resolution workflow"
          icon={<ShieldAlert className="h-4 w-4" />}
          accentColor={openCount > 0 ? 'amber' : 'brand'}
        />
        <MetricCard
          title="Resolved"
          value={isLoading ? '—' : resolvedCount}
          subtitle="Recovered service states"
          icon={<RefreshCw className="h-4 w-4" />}
          accentColor="emerald"
        />
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-3 shadow-xs transition-colors sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 sm:max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-surface-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('incidents.searchIncidents')}
            className="w-full rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 py-1.5 pl-8 pr-3 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:bg-white dark:focus:bg-surface-900 focus:outline-none transition-colors"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 px-2.5 py-1.5 text-xs font-medium text-surface-700 dark:text-surface-300 focus:outline-none"
          >
            <option value="all">{t('incidents.allSeverities')}</option>
            <option value="critical">{t('incidents.critical')}</option>
            <option value="warning">{t('incidents.warning')}</option>
            <option value="info">{t('incidents.info')}</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 px-2.5 py-1.5 text-xs font-medium text-surface-700 dark:text-surface-300 focus:outline-none"
          >
            <option value="all">{t('incidents.allStatuses')}</option>
            <option value="open">{t('incidents.open')}</option>
            <option value="acknowledged">{t('incidents.acknowledged')}</option>
            <option value="in_progress">{t('incidents.inProgress')}</option>
            <option value="resolved">{t('incidents.resolved')}</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-xs transition-colors">
        {isLoading ? (
          <div className="p-6 space-y-3">
            <LoadingSkeleton height="h-10" />
            <LoadingSkeleton height="h-10" />
            <LoadingSkeleton height="h-10" />
          </div>
        ) : error ? (
          <div className="p-6 text-center text-xs text-rose-600 dark:text-rose-400">
            {t('dashboard.errorLoading')}
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div className="py-12">
            <EmptyState
              icon={<ShieldAlert className="h-8 w-8" />}
              title={t('incidents.noIncidents')}
              description="No active or historical incidents found matching your criteria."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-surface-700 dark:text-surface-300">
              <thead className="border-b border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                <tr>
                  <th className="py-3.5 px-4">ID</th>
                  <th className="py-3.5 px-4">{t('common.priority')}</th>
                  <th className="py-3.5 px-4">{t('common.status')}</th>
                  <th className="py-3.5 px-4">{t('common.title')}</th>
                  <th className="py-3.5 px-4">{t('incidents.occurrenceCount')}</th>
                  <th className="py-3.5 px-4">{t('incidents.lastSeen')}</th>
                  <th className="py-3.5 px-4 text-right">{t('common.action')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-surface-800/80">
                {filteredIncidents.map((inc) => (
                  <tr
                    key={inc.id}
                    className="hover:bg-surface-50/70 dark:hover:bg-surface-800/40 transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-surface-600 dark:text-surface-400">
                      #{inc.id}
                    </td>
                    <td className="py-3.5 px-4">{getSeverityBadge(inc.severity)}</td>
                    <td className="py-3.5 px-4">{getStatusBadge(inc.status)}</td>
                    <td className="py-3.5 px-4 max-w-sm">
                      <p className="font-bold text-surface-900 dark:text-white truncate">{inc.title}</p>
                      <p className="text-[11px] text-surface-500 dark:text-surface-400 truncate">
                        {inc.description}
                      </p>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-surface-900 dark:text-white">
                      {inc.occurrence_count}
                    </td>
                    <td className="py-3.5 px-4 text-surface-500 dark:text-surface-400 font-mono">
                      {new Date(inc.last_seen_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {canRespond && inc.status === 'open' && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => ackMutation.mutate(inc.id)}
                            isLoading={ackMutation.isPending}
                          >
                            {t('incidents.acknowledge')}
                          </Button>
                        )}
                        {canRespond && inc.status !== 'resolved' && (
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => setResolvingIncident(inc)}
                          >
                            {t('incidents.resolve')}
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/incidents/${inc.id}`)}
                        >
                          {t('incidents.details')}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {resolvingIncident && (
        <ResolveIncidentModal
          incidentId={resolvingIncident.id}
          incidentTitle={resolvingIncident.title}
          onClose={() => setResolvingIncident(null)}
        />
      )}
    </div>
  );
};
