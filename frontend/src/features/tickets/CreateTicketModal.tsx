import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { LifeBuoy, X } from 'lucide-react';
import { ticketsApi } from '../../shared/api/tickets';
import { Button } from '../../shared/components/Button';

interface CreateTicketModalProps {
  onClose: () => void;
}

export const CreateTicketModal: React.FC<CreateTicketModalProps> = ({ onClose }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('general');
  const [priority, setPriority] = useState('medium');
  const [deviceId, setDeviceId] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      ticketsApi.createTicket({
        title: title.trim(),
        description: description.trim(),
        category,
        priority,
        device_id: deviceId ? Number(deviceId) : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ticketsList'] });
      onClose();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMsg(msg || 'Failed to submit ticket');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setErrorMsg('Please enter both title and description');
      return;
    }
    setErrorMsg(null);
    createMutation.mutate();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div className="relative w-full max-w-lg rounded-2xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-2xl transition-colors">
        <div className="flex items-center justify-between border-b border-surface-200 dark:border-surface-800 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500/10 text-brand-600 dark:text-brand-400">
              <LifeBuoy className="h-4 w-4" />
            </div>
            <h3 className="text-base font-bold text-surface-900 dark:text-white">
              {t('helpdesk.newTicket')}
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
          {errorMsg && (
            <div className="rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-2.5 text-xs font-semibold text-rose-700 dark:text-rose-300">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
              {t('common.title')}
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Masalan: Monitor yoqilmayapti yoki Wi-Fi uzildi"
              className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
                {t('helpdesk.category')}
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="general">General</option>
                <option value="hardware">Hardware</option>
                <option value="software">Software</option>
                <option value="network">Network & Connectivity</option>
                <option value="access">Access & Permissions</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
                {t('helpdesk.priority')}
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="low">{t('helpdesk.low')}</option>
                <option value="medium">{t('helpdesk.medium')}</option>
                <option value="high">{t('helpdesk.high')}</option>
                <option value="urgent">{t('helpdesk.urgent')}</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
              Description (Detailed explanation of the issue)
            </label>
            <textarea
              required
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Muammo qachon boshlandi, qanday xatolik ko'rsatmoqda..."
              className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 p-2.5 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
              Associated Device ID (Optional)
            </label>
            <input
              type="number"
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              placeholder="e.g. 1"
              className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" size="sm" onClick={onClose}>
              {t('incidents.cancel')}
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={createMutation.isPending}>
              {createMutation.isPending ? 'Submitting...' : t('helpdesk.newTicket')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
