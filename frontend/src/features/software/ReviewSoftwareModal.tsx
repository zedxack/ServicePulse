import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, XCircle, X } from 'lucide-react';
import { softwareApi } from '../../shared/api/software';
import { SoftwareRequestRead } from '../../shared/types/software';
import { Button } from '../../shared/components/Button';

interface ReviewSoftwareModalProps {
  request: SoftwareRequestRead;
  action: 'approve' | 'reject';
  onClose: () => void;
}

export const ReviewSoftwareModal: React.FC<ReviewSoftwareModalProps> = ({
  request,
  action,
  onClose,
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [reviewNotes, setReviewNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isApprove = action === 'approve';

  const reviewMutation = useMutation({
    mutationFn: () => {
      const data = { review_notes: reviewNotes.trim() || undefined };
      return isApprove
        ? softwareApi.approveSoftwareRequest(request.id, data)
        : softwareApi.rejectSoftwareRequest(request.id, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['softwareRequests'] });
      onClose();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMsg(msg || 'Failed to review request');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    reviewMutation.mutate();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div className="relative w-full max-w-md rounded-2xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-2xl transition-colors">
        <div className="flex items-center justify-between border-b border-surface-200 dark:border-surface-800 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                isApprove
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                  : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
              }`}
            >
              {isApprove ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            </div>
            <h3 className="text-base font-bold text-surface-900 dark:text-white">
              {isApprove ? t('softwareApproval.approve') : t('softwareApproval.reject')}
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
          <div className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 p-3 text-xs space-y-1.5 text-surface-700 dark:text-surface-300">
            <p>
              Software: <span className="font-bold text-surface-900 dark:text-white">{request.software_name}</span>
            </p>
            <p className="text-surface-600 dark:text-surface-400">
              Device ID: <span className="font-mono">#{request.device_id}</span> &bull; Author: User #{request.user_id}
            </p>
            <p className="text-surface-600 dark:text-surface-400">
              Justification: <span className="italic">{request.reason}</span>
            </p>
          </div>

          {errorMsg && (
            <div className="rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-2.5 text-xs font-semibold text-rose-700 dark:text-rose-300">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
              {t('softwareApproval.reviewNotes')}
            </label>
            <textarea
              rows={3}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder={t('softwareApproval.reviewNotesPlaceholder')}
              className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 p-2.5 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" size="sm" onClick={onClose}>
              {t('incidents.cancel')}
            </Button>
            <Button
              type="submit"
              variant={isApprove ? 'primary' : 'danger'}
              size="sm"
              isLoading={reviewMutation.isPending}
            >
              {reviewMutation.isPending
                ? 'Processing...'
                : isApprove
                ? t('softwareApproval.approve')
                : t('softwareApproval.reject')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
