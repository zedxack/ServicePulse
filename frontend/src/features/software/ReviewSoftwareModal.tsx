import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, XCircle, X } from 'lucide-react';
import { softwareApi } from '../../shared/api/software';
import { SoftwareRequestRead } from '../../shared/types/software';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
      <div className="relative w-full max-w-md rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                isApprove ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'
              }`}
            >
              {isApprove ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            </div>
            <h3 className="text-base font-bold text-surface-900">
              {isApprove ? t('softwareApproval.approve') : t('softwareApproval.reject')}
            </h3>
          </div>
          <button onClick={onClose} aria-label="Close dialog" className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="rounded-lg bg-surface-50 p-3 text-xs space-y-1">
            <p>
              Dastur: <span className="font-bold text-surface-900">{request.software_name}</span>
            </p>
            <p className="text-surface-600">
              Qurilma ID: <span className="font-mono">#{request.device_id}</span> &bull; Foydalanuvchi: #{request.user_id}
            </p>
            <p className="text-surface-600">
              Asos: <span className="italic">{request.reason}</span>
            </p>
          </div>

          {errorMsg && (
            <div className="rounded-lg bg-rose-50 p-2.5 text-xs font-semibold text-rose-700">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-surface-700 mb-1">
              {t('softwareApproval.reviewNotes')}
            </label>
            <textarea
              rows={3}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder={t('softwareApproval.reviewNotesPlaceholder')}
              className="w-full rounded-lg border border-surface-300 p-2.5 text-xs text-surface-900 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg bg-surface-100 px-4 py-2 text-xs font-semibold text-surface-700 hover:bg-surface-200"
            >
              {t('incidents.cancel')}
            </button>
            <button
              type="submit"
              disabled={reviewMutation.isPending}
              className={`rounded-lg px-4 py-2 text-xs font-semibold text-white shadow-xs disabled:opacity-50 ${
                isApprove ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'
              }`}
            >
              {reviewMutation.isPending
                ? 'Saqlanmoqda...'
                : isApprove
                ? t('softwareApproval.approve')
                : t('softwareApproval.reject')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
