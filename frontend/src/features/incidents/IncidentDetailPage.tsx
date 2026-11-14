import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Fingerprint,
  History,
  Shield,
  UserCheck,
  Wrench,
} from 'lucide-react';
import { incidentsApi } from '../../shared/api/incidents';
import { useAuth } from '../auth/AuthContext';
import { ResolveIncidentModal } from './ResolveIncidentModal';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';

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
      <div className="space-y-6">
        <LoadingSkeleton height="h-8" width="w-48" />
        <LoadingSkeleton height="h-64" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <LoadingSkeleton height="h-64" />
          <LoadingSkeleton height="h-64" />
        </div>
      </div>
    );
  }

  if (incidentError || !incident) {
    return (
      <div className="rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/20 p-6 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-rose-600 dark:text-rose-400 mb-2" />
        <h3 className="text-sm font-bold text-rose-900 dark:text-rose-200">{t('dashboard.errorLoading')}</h3>
        <button
          onClick={() => navigate('/incidents')}
          className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-rose-700 dark:text-rose-300 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Incidents</span>
        </button>
      </div>
    );
  }

  const getSeverityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return <Badge variant="offline" size="md">{t('incidents.critical')}</Badge>;
      case 'warning':
        return <Badge variant="warning" size="md">{t('incidents.warning')}</Badge>;
      default:
        return <Badge variant="info" size="md">{t('incidents.info')}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open':
        return <Badge variant="offline" size="md">{t('incidents.open')}</Badge>;
      case 'acknowledged':
        return <Badge variant="warning" size="md">{t('incidents.acknowledged')}</Badge>;
      case 'in_progress':
        return <Badge variant="brand" size="md">{t('incidents.inProgress')}</Badge>;
      case 'resolved':
        return <Badge variant="online" size="md">{t('incidents.resolved')}</Badge>;
      default:
        return <Badge variant="mono" size="md">{status}</Badge>;
    }
  };

  const isResolved = incident.status === 'resolved';

  return (
    <div className="space-y-6">
      {/* Navigation & Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <button
          onClick={() => navigate('/incidents')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Incidents</span>
        </button>

        {canRespond && (
          <div className="flex items-center gap-2">
            {!isResolved && incident.status === 'open' && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => ackMutation.mutate()}
                isLoading={ackMutation.isPending}
                leftIcon={<CheckCircle2 className="h-3.5 w-3.5" />}
              >
                {t('incidents.acknowledge')}
              </Button>
            )}

            {!isResolved && (!incident.assigned_to_user_id || incident.assigned_to_user_id !== user?.id) && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => assignMutation.mutate()}
                isLoading={assignMutation.isPending}
                leftIcon={<UserCheck className="h-3.5 w-3.5" />}
              >
                Assign to Me
              </Button>
            )}

            {!isResolved && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsResolveModalOpen(true)}
                leftIcon={<CheckCircle2 className="h-3.5 w-3.5" />}
              >
                {t('incidents.resolve')}
              </Button>
            )}
          </div>
        )}
      </div>

      {actionError && (
        <div className="rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-3 text-xs font-medium text-rose-700 dark:text-rose-300">
          {actionError}
        </div>
      )}

      {/* Main Incident Card */}
      <div className="rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-6 shadow-xs transition-colors">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-xs font-bold text-surface-500 dark:text-surface-400">
                #{incident.id}
              </span>
              {getSeverityBadge(incident.severity)}
              {getStatusBadge(incident.status)}
            </div>
            <h1 className="text-xl font-bold text-surface-900 dark:text-white">{incident.title}</h1>
            <p className="mt-1 text-xs text-surface-600 dark:text-surface-300">{incident.description}</p>
          </div>

          <div className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 p-3.5 text-right">
            <span className="text-[10px] font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wider">
              {t('incidents.occurrenceCount')}
            </span>
            <p className="font-mono text-2xl font-bold text-surface-900 dark:text-white">
              {incident.occurrence_count}
            </p>
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="mt-6 grid grid-cols-2 gap-4 border-t border-surface-100 dark:border-surface-800 pt-4 sm:grid-cols-4 text-xs">
          <div>
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
              {t('incidents.firstSeen')}
            </span>
            <p className="font-mono font-medium text-surface-900 dark:text-white">
              {new Date(incident.first_seen_at).toLocaleString()}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
              {t('incidents.lastSeen')}
            </span>
            <p className="font-mono font-medium text-surface-900 dark:text-white">
              {new Date(incident.last_seen_at).toLocaleString()}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
              {t('incidents.assignedTo')}
            </span>
            <p className="font-semibold text-surface-900 dark:text-white">
              {incident.assigned_to_user_id ? `User #${incident.assigned_to_user_id}` : t('incidents.unassigned')}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">Device ID</span>
            <p className="font-mono text-surface-900 dark:text-white">
              {incident.device_id ? `#${incident.device_id}` : '—'}
            </p>
          </div>
        </div>

        {/* Fingerprint & Deduplication info */}
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg bg-surface-50 dark:bg-surface-950/50 border border-surface-200 dark:border-surface-800 p-2.5 text-[11px] font-mono text-surface-600 dark:text-surface-400">
          <Fingerprint className="h-3.5 w-3.5 text-surface-400" />
          <span className="font-bold">Fingerprint:</span>
          <span>{incident.fingerprint}</span>
          {incident.active_dedup_key && (
            <span className="rounded bg-brand-500/10 border border-brand-500/20 px-1 text-[10px] text-brand-700 dark:text-brand-300">
              Active Dedup
            </span>
          )}
        </div>

        {incident.resolution_notes && (
          <div className="mt-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 p-4 border border-emerald-200 dark:border-emerald-800/50">
            <h4 className="text-xs font-bold text-emerald-900 dark:text-emerald-200">
              {t('incidents.resolutionNotes')}
            </h4>
            <p className="mt-1 text-xs text-emerald-800 dark:text-emerald-300">{incident.resolution_notes}</p>
            {incident.resolved_at && (
              <p className="mt-2 text-[10px] text-emerald-600 dark:text-emerald-400 font-mono">
                Resolved at: {new Date(incident.resolved_at).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Two Columns: Event History Timeline & Remediation Executions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Event History */}
        <div className="rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-6 shadow-xs transition-colors">
          <div className="flex items-center gap-2 mb-4">
            <History className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            <h3 className="text-sm font-bold text-surface-900 dark:text-white">
              {t('incidents.eventHistory')}
            </h3>
          </div>

          {eventsLoading ? (
            <div className="space-y-3">
              <LoadingSkeleton height="h-12" />
              <LoadingSkeleton height="h-12" />
            </div>
          ) : !events || events.length === 0 ? (
            <div className="py-6 text-center text-xs text-surface-400">{t('incidents.noEvents')}</div>
          ) : (
            <div className="space-y-4">
              {events.map((evt, idx) => (
                <div key={evt.id || idx} className="relative flex gap-3 pb-4">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-500/10 text-brand-600 dark:text-brand-400 ring-2 ring-white dark:ring-surface-900">
                    <Clock className="h-3 w-3" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold uppercase tracking-wider text-[10px] text-brand-600 dark:text-brand-400">
                        {evt.event_type}
                      </span>
                      <span className="text-[10px] font-mono text-surface-400">
                        {new Date(evt.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-surface-700 dark:text-surface-300">{evt.message}</p>
                    {evt.payload && (
                      <pre className="mt-1 max-w-full overflow-x-auto rounded bg-surface-50 dark:bg-surface-950/60 p-2 font-mono text-[10px] text-surface-600 dark:text-surface-400 border border-surface-200 dark:border-surface-800">
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
        <div className="rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-6 shadow-xs transition-colors">
          <div className="flex items-center gap-2 mb-4">
            <Wrench className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <h3 className="text-sm font-bold text-surface-900 dark:text-white">
              {t('incidents.remediations')}
            </h3>
          </div>

          {!canRespond ? (
            <div className="py-8 text-center text-xs text-surface-500 dark:text-surface-400">
              <Shield className="mx-auto h-6 w-6 text-surface-400 mb-2" />
              <p className="font-semibold text-surface-700 dark:text-surface-300">
                Remediation details restricted
              </p>
              <p className="mt-1 text-[11px] text-surface-400">
                Automated action logs are visible only to authorized IT operators.
              </p>
            </div>
          ) : relatedRemediations.length === 0 ? (
            <div className="py-8 text-center text-xs text-surface-400">
              {t('incidents.noRemediations')}
            </div>
          ) : (
            <div className="divide-y divide-surface-100 dark:divide-surface-800">
              {relatedRemediations.map((rem) => {
                const isSuccess = rem.status === 'succeeded';
                const isFailed = rem.status === 'failed';

                return (
                  <div key={rem.id} className="py-3 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-surface-900 dark:text-white font-mono">
                        Execution #{rem.id}
                      </span>
                      <Badge
                        variant={isSuccess ? 'online' : isFailed ? 'offline' : 'warning'}
                        size="sm"
                      >
                        {rem.status}
                      </Badge>
                    </div>
                    <p className="text-surface-600 dark:text-surface-400 text-[11px] font-mono break-all">
                      {rem.execution_log || 'No log details'}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-surface-400 pt-1">
                      <span>
                        Verification:{' '}
                        <b className="capitalize text-surface-700 dark:text-surface-300">
                          {rem.verification_status}
                        </b>
                      </span>
                      <span className="font-mono">{new Date(rem.created_at).toLocaleString()}</span>
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
