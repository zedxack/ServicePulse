import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  RefreshCw,
  Search,
  ShieldAlert,
} from 'lucide-react';
import { incidentsApi } from '../../shared/api/incidents';
import { IncidentRead } from '../../shared/types/incident';
import { ResolveIncidentModal } from './ResolveIncidentModal';
import { useAuth } from '../auth/AuthContext';

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
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-700 ring-1 ring-rose-200">
            <AlertTriangle className="h-3 w-3 text-rose-600" />
            {t('incidents.critical')}
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700 ring-1 ring-amber-200">
            <AlertCircle className="h-3 w-3 text-amber-600" />
            {t('incidents.warning')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700 ring-1 ring-blue-200">
            <Info className="h-3 w-3 text-blue-600" />
            {t('incidents.info')}
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700 ring-1 ring-rose-200">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            {t('incidents.open')}
          </span>
        );
      case 'acknowledged':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700 ring-1 ring-amber-200">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {t('incidents.acknowledged')}
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700 ring-1 ring-blue-200">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            {t('incidents.inProgress')}
          </span>
        );
      case 'resolved':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t('incidents.resolved')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2 py-0.5 text-[11px] font-semibold text-surface-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-surface-900">{t('incidents.title')}</h2>
          <p className="text-xs text-surface-500">{t('incidents.subtitle')}</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-semibold text-surface-700 shadow-xs hover:bg-surface-50"
        >
          <RefreshCw className="h-3.5 w-3.5 text-surface-500" />
          <span>{t('dashboard.refresh')}</span>
        </button>
      </div>

      {/* Counters */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-medium text-surface-500">Jami Hodisalar</span>
          <p className="mt-2 text-2xl font-bold text-surface-900">
            {isLoading ? '—' : incidentData?.total ?? 0}
          </p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-medium text-rose-600">Kritik Avariyalar</span>
          <p className="mt-2 text-2xl font-bold text-rose-600">{isLoading ? '—' : criticalCount}</p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-medium text-amber-600">Ochiq Hodisalar</span>
          <p className="mt-2 text-2xl font-bold text-amber-600">{isLoading ? '—' : openCount}</p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-medium text-emerald-600">Hal Qilingan</span>
          <p className="mt-2 text-2xl font-bold text-emerald-600">{isLoading ? '—' : resolvedCount}</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 bg-white p-3 shadow-xs sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 sm:max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-surface-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('incidents.searchIncidents')}
            className="w-full rounded-lg border border-surface-200 bg-surface-50 py-1.5 pl-8 pr-3 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:bg-white focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="rounded-lg border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-xs font-medium text-surface-700 focus:outline-none"
          >
            <option value="all">{t('incidents.allSeverities')}</option>
            <option value="critical">{t('incidents.critical')}</option>
            <option value="warning">{t('incidents.warning')}</option>
            <option value="info">{t('incidents.info')}</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="rounded-lg border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-xs font-medium text-surface-700 focus:outline-none"
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
      <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs">
        {isLoading ? (
          <div className="py-12 text-center text-xs text-surface-500">{t('dashboard.loading')}</div>
        ) : error ? (
          <div className="p-6 text-center text-xs text-rose-600">{t('dashboard.errorLoading')}</div>
        ) : filteredIncidents.length === 0 ? (
          <div className="py-12 text-center text-xs text-surface-500">
            <ShieldAlert className="mx-auto h-8 w-8 text-surface-300 mb-2" />
            <p className="font-semibold text-surface-700">{t('incidents.noIncidents')}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-surface-700">
              <thead className="border-b border-surface-200 bg-surface-50/75 text-[11px] font-semibold uppercase tracking-wider text-surface-500">
                <tr>
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">{t('common.priority')}</th>
                  <th className="py-3 px-4">{t('common.status')}</th>
                  <th className="py-3 px-4">{t('common.title')}</th>
                  <th className="py-3 px-4">{t('incidents.occurrenceCount')}</th>
                  <th className="py-3 px-4">{t('incidents.lastSeen')}</th>
                  <th className="py-3 px-4 text-right">{t('common.action')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {filteredIncidents.map((inc) => (
                  <tr key={inc.id} className="hover:bg-surface-50/50 transition">
                    <td className="py-3 px-4 font-mono font-bold text-surface-600">#{inc.id}</td>
                    <td className="py-3 px-4">{getSeverityBadge(inc.severity)}</td>
                    <td className="py-3 px-4">{getStatusBadge(inc.status)}</td>
                    <td className="py-3 px-4 max-w-sm">
                      <p className="font-bold text-surface-900 truncate">{inc.title}</p>
                      <p className="text-[11px] text-surface-500 truncate">{inc.description}</p>
                    </td>
                    <td className="py-3 px-4 font-bold text-surface-900">{inc.occurrence_count}</td>
                    <td className="py-3 px-4 text-surface-500">
                      {new Date(inc.last_seen_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {canRespond && inc.status === 'open' && (
                          <button
                            onClick={() => ackMutation.mutate(inc.id)}
                            disabled={ackMutation.isPending}
                            className="rounded-md bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-700 hover:bg-amber-100 disabled:opacity-50"
                          >
                            {t('incidents.acknowledge')}
                          </button>
                        )}
                        {canRespond && inc.status !== 'resolved' && (
                          <button
                            onClick={() => setResolvingIncident(inc)}
                            className="rounded-md bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700 hover:bg-emerald-100"
                          >
                            {t('incidents.resolve')}
                          </button>
                        )}
                        <button
                          onClick={() => navigate(`/incidents/${inc.id}`)}
                          className="rounded-md bg-surface-100 px-2.5 py-1 text-[11px] font-semibold text-brand-700 hover:bg-brand-50"
                        >
                          {t('incidents.details')}
                        </button>
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
