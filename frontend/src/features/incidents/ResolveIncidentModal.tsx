import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, X } from 'lucide-react';
import { incidentsApi } from '../../shared/api/incidents';
import { Button } from '../../shared/components/Button';

interface ResolveIncidentModalProps {
  incidentId: number;
  incidentTitle: string;
  onClose: () => void;
}

export const ResolveIncidentModal: React.FC<ResolveIncidentModalProps> = ({
  incidentId,
  incidentTitle,
  onClose,
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const resolveMutation = useMutation({
    mutationFn: () =>
      incidentsApi.resolveIncident(incidentId, {
        resolution_notes: resolutionNotes.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidentsList'] });
      queryClient.invalidateQueries({ queryKey: ['incidentDetail', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incidentEvents', incidentId] });
      onClose();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMsg(msg || 'Failed to resolve incident');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (resolutionNotes.trim().length < 3) {
      setErrorMsg('Resolution notes must be at least 3 characters.');
      return;
    }
    setErrorMsg(null);
    resolveMutation.mutate();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div className="relative w-full max-w-md rounded-2xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-2xl transition-colors">
        <div className="flex items-center justify-between border-b border-surface-200 dark:border-surface-800 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
            </div>
            <h3 className="text-base font-bold text-surface-900 dark:text-white">
              {t('incidents.resolve')}
            </h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800 hover:text-surface-700 dark:hover:text-surface-200 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <p className="text-xs text-surface-600 dark:text-surface-300">
            Incident: <span className="font-bold text-surface-900 dark:text-white">{incidentTitle}</span>
          </p>

          {errorMsg && (
            <div className="rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-2.5 text-xs font-semibold text-rose-700 dark:text-rose-300">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
              {t('incidents.resolutionNotes')}
            </label>
            <textarea
              required
              rows={3}
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder={t('incidents.resolutionNotesPlaceholder')}
              className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 p-2.5 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" size="sm" onClick={onClose}>
              {t('incidents.cancel')}
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={resolveMutation.isPending}>
              {resolveMutation.isPending ? 'Resolving...' : t('incidents.resolve')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
