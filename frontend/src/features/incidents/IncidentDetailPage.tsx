import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Fingerprint,
  History,
  Info,
  RefreshCw,
  Shield,
  UserCheck,
  Wrench,
} from 'lucide-react';
import { incidentsApi } from '../../shared/api/incidents';
import { useAuth } from '../auth/AuthContext';
import { ResolveIncidentModal } from './ResolveIncidentModal';

export const IncidentDetailPage: React.FC = () => {
  const { incidentId } = useParams<{ incidentId: string }>();
  const id = Number(incidentId);
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, hasAnyRole } = useAuth();
  const queryClient = useQueryClient();
  const [isResolveModalOpen, setIsResolveModalOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const canRespond = hasAnyRole(['platform_super_admin', 'company_admin', 'it_admin', 'support', 'admin']);

  const {
    data: incident,
    isLoading: incidentLoading,
    error: incidentError,
  } = useQuery({
    queryKey: ['incidentDetail', id],
    queryFn: () => incidentsApi.getIncident(id),
    enabled: !!id,
  });

  const {
    data: events,
    isLoading: eventsLoading,
  } = useQuery({
    queryKey: ['incidentEvents', id],
    queryFn: () => incidentsApi.getIncidentEvents(id),
    enabled: !!id,
  });

  const { data: remediations } = useQuery({
    queryKey: ['incidentRemediations', id],
    queryFn: () => incidentsApi.listRemediationExecutions({ incident_id: id, limit: 50 }),
    enabled: !!id && canRespond,
  });

  const relatedRemediations = remediations || [];

  const ackMutation = useMutation({
    mutationFn: () => incidentsApi.acknowledgeIncident(id, { notes: 'Acknowledged via UI' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidentDetail', id] });
      queryClient.invalidateQueries({ queryKey: ['incidentEvents', id] });
      queryClient.invalidateQueries({ queryKey: ['incidentsList'] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(msg || 'Failed to acknowledge incident');
    },
  });

  const assignMutation = useMutation({
    mutationFn: () => {
      if (!user) throw new Error('User not logged in');
      return incidentsApi.assignIncident(id, { assigned_to_user_id: user.id });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidentDetail', id] });
      queryClient.invalidateQueries({ queryKey: ['incidentEvents', id] });
      queryClient.invalidateQueries({ queryKey: ['incidentsList'] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(msg || 'Failed to assign incident');
    },
  });

  if (incidentLoading) {
    return (
      <div className="py-16 text-center text-xs text-surface-500">
        <RefreshCw className="mx-auto h-6 w-6 animate-spin text-brand-500 mb-2" />
        {t('dashboard.loading')}
      </div>
    );
  }

  if (incidentError || !incident) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-rose-600 mb-2" />
        <h3 className="text-sm font-bold text-rose-900">{t('dashboard.errorLoading')}</h3>
        <button
          onClick={() => navigate('/incidents')}
          className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-rose-700 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Hodisalar ro'yxatiga qaytish</span>
        </button>
      </div>
    );
  }

  const getSeverityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-800">
            <AlertTriangle className="h-3.5 w-3.5 text-rose-600" />
            {t('incidents.critical')}
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-800">
            <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
            {t('incidents.warning')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-bold text-blue-800">
            <Info className="h-3.5 w-3.5 text-blue-600" />
            {t('incidents.info')}
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-700 ring-1 ring-rose-200">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            {t('incidents.open')}
          </span>
        );
      case 'acknowledged':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 ring-1 ring-amber-200">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {t('incidents.acknowledged')}
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-200">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            {t('incidents.inProgress')}
          </span>
        );
      case 'resolved':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t('incidents.resolved')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2.5 py-0.5 text-xs font-semibold text-surface-700">
            {status}
          </span>
        );
    }
  };

  const isResolved = incident.status === 'resolved';

  return (
    <div className="space-y-6">
      {/* Navigation & Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <button
          onClick={() => navigate('/incidents')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-surface-600 hover:text-surface-900"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Hodisalar ro'yxatiga qaytish</span>
        </button>

        {canRespond && (
          <div className="flex items-center gap-2">
            {!isResolved && incident.status === 'open' && (
              <button
                onClick={() => ackMutation.mutate()}
                disabled={ackMutation.isPending}
                className="flex items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50"
              >
                <CheckCircle2 className="h-3.5 w-3.5 text-amber-600" />
                <span>{ackMutation.isPending ? 'Saqlanmoqda...' : t('incidents.acknowledge')}</span>
              </button>
            )}

            {!isResolved && (!incident.assigned_to_user_id || incident.assigned_to_user_id !== user?.id) && (
              <button
                onClick={() => assignMutation.mutate()}
                disabled={assignMutation.isPending}
                className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-semibold text-surface-700 hover:bg-surface-50 disabled:opacity-50"
              >
                <UserCheck className="h-3.5 w-3.5 text-brand-600" />
                <span>Menga biriktirish</span>
              </button>
            )}

            {!isResolved && (
              <button
                onClick={() => setIsResolveModalOpen(true)}
                className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-emerald-700"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{t('incidents.resolve')}</span>
              </button>
            )}
          </div>
        )}
      </div>

      {actionError && (
        <div className="rounded-lg bg-rose-50 p-3 text-xs font-medium text-rose-700">
          {actionError}
        </div>
      )}

      {/* Main Incident Card */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-xs">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-mono text-xs font-bold text-surface-500">#{incident.id}</span>
              {getSeverityBadge(incident.severity)}
              {getStatusBadge(incident.status)}
            </div>
            <h1 className="text-lg font-bold text-surface-900">{incident.title}</h1>
            <p className="mt-1 text-xs text-surface-600">{incident.description}</p>
          </div>

          <div className="rounded-lg border border-surface-200 bg-surface-50 p-3 text-right">
            <span className="text-[10px] font-semibold text-surface-500 uppercase tracking-wider">
              {t('incidents.occurrenceCount')}
            </span>
            <p className="text-xl font-bold text-surface-900">{incident.occurrence_count}</p>
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="mt-6 grid grid-cols-2 gap-4 border-t border-surface-100 pt-4 sm:grid-cols-4 text-xs">
          <div>
            <span className="text-[11px] font-medium text-surface-500">{t('incidents.firstSeen')}</span>
            <p className="font-medium text-surface-900">{new Date(incident.first_seen_at).toLocaleString()}</p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500">{t('incidents.lastSeen')}</span>
            <p className="font-medium text-surface-900">{new Date(incident.last_seen_at).toLocaleString()}</p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500">{t('incidents.assignedTo')}</span>
            <p className="font-semibold text-surface-900">
              {incident.assigned_to_user_id ? `User #${incident.assigned_to_user_id}` : t('incidents.unassigned')}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500">Device ID</span>
            <p className="font-mono text-surface-900">{incident.device_id ? `#${incident.device_id}` : '—'}</p>
          </div>
        </div>

        {/* Fingerprint & Deduplication info */}
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg bg-surface-50 p-2.5 text-[11px] font-mono text-surface-600">
          <Fingerprint className="h-3.5 w-3.5 text-surface-400" />
          <span className="font-bold">Fingerprint:</span>
          <span>{incident.fingerprint}</span>
          {incident.active_dedup_key && (
            <span className="rounded bg-brand-100 px-1 text-[10px] text-brand-800">Active Dedup</span>
          )}
        </div>

        {incident.resolution_notes && (
          <div className="mt-4 rounded-lg bg-emerald-50 p-4 border border-emerald-200">
            <h4 className="text-xs font-bold text-emerald-900">{t('incidents.resolutionNotes')}</h4>
            <p className="mt-1 text-xs text-emerald-800">{incident.resolution_notes}</p>
            {incident.resolved_at && (
              <p className="mt-2 text-[10px] text-emerald-600">
                Hal etilgan vaqt: {new Date(incident.resolved_at).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Two Columns: Event History Timeline & Remediation Executions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Event History */}
        <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-xs">
          <div className="flex items-center gap-2 mb-4">
            <History className="h-4 w-4 text-brand-600" />
            <h3 className="text-sm font-bold text-surface-900">{t('incidents.eventHistory')}</h3>
          </div>

          {eventsLoading ? (
            <div className="py-6 text-center text-xs text-surface-500">{t('dashboard.loading')}</div>
          ) : !events || events.length === 0 ? (
            <div className="py-6 text-center text-xs text-surface-500">{t('incidents.noEvents')}</div>
          ) : (
            <div className="space-y-4">
              {events.map((evt, idx) => (
                <div key={evt.id || idx} className="relative flex gap-3 pb-4">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600 ring-2 ring-white">
                    <Clock className="h-3 w-3" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold uppercase tracking-wider text-[10px] text-brand-700">
                        {evt.event_type}
                      </span>
                      <span className="text-[10px] text-surface-400">
                        {new Date(evt.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-surface-700">{evt.message}</p>
                    {evt.payload && (
                      <pre className="mt-1 max-w-full overflow-x-auto rounded bg-surface-50 p-2 font-mono text-[10px] text-surface-600">
                        {evt.payload}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Automated Remediations */}
        <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-xs">
          <div className="flex items-center gap-2 mb-4">
            <Wrench className="h-4 w-4 text-emerald-600" />
            <h3 className="text-sm font-bold text-surface-900">{t('incidents.remediations')}</h3>
          </div>

          {!canRespond ? (
            <div className="py-8 text-center text-xs text-surface-500">
              <Shield className="mx-auto h-6 w-6 text-surface-400 mb-2" />
              <p className="font-semibold text-surface-700">Tuzatish tafsilotlari cheklangan</p>
              <p className="mt-1 text-[11px] text-surface-400">
                Avtomatik tuzatish auditi faqat vakolatli IT xodimlari uchun ko'rsatiladi.
              </p>
            </div>
          ) : relatedRemediations.length === 0 ? (
            <div className="py-8 text-center text-xs text-surface-500">
              {t('incidents.noRemediations')}
            </div>
          ) : (
            <div className="divide-y divide-surface-100">
              {relatedRemediations.map((rem) => {
                const isSuccess = rem.status === 'succeeded';
                const isFailed = rem.status === 'failed';
                const statusBadgeClass = isSuccess
                  ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
                  : isFailed
                  ? 'bg-rose-50 text-rose-700 ring-1 ring-rose-200'
                  : 'bg-amber-50 text-amber-700 ring-1 ring-amber-200';

                return (
                  <div key={rem.id} className="py-3 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-surface-900">Execution #{rem.id}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize ${statusBadgeClass}`}>
                        {rem.status}
                      </span>
                    </div>
                    <p className="text-surface-600 text-[11px] font-mono break-all">{rem.execution_log || 'No log details'}</p>
                    <div className="flex items-center justify-between text-[10px] text-surface-400 pt-1">
                      <span>Verification: <b className="capitalize text-surface-700">{rem.verification_status}</b></span>
                      <span>{new Date(rem.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {isResolveModalOpen && (
        <ResolveIncidentModal
          incidentId={incident.id}
          incidentTitle={incident.title}
          onClose={() => setIsResolveModalOpen(false)}
        />
      )}
    </div>
  );
};
