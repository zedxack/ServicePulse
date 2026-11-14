import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { LifeBuoy, X } from 'lucide-react';
import { ticketsApi } from '../../shared/api/tickets';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
      <div className="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <LifeBuoy className="h-4 w-4" />
            </div>
            <h3 className="text-base font-bold text-surface-900">{t('helpdesk.newTicket')}</h3>
          </div>
          <button onClick={onClose} aria-label="Close dialog" className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="rounded-lg bg-rose-50 p-2.5 text-xs font-semibold text-rose-700">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-surface-700 mb-1">
              {t('common.title')}
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Masalan: Monitor yoqilmayapti yoki Wi-Fi uzildi"
              className="w-full rounded-lg border border-surface-300 px-3 py-2 text-xs focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-surface-700 mb-1">
                {t('helpdesk.category')}
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-lg border border-surface-300 px-3 py-2 text-xs focus:border-brand-500 focus:outline-none"
              >
                <option value="general">Umumiy</option>
                <option value="hardware">Uskuna (Hardware)</option>
                <option value="software">Dasturiy Ta'minot</option>
                <option value="network">Tarmoq & Internet</option>
                <option value="access">Kirish & Huquqlar</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-surface-700 mb-1">
                {t('helpdesk.priority')}
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded-lg border border-surface-300 px-3 py-2 text-xs focus:border-brand-500 focus:outline-none"
              >
                <option value="low">{t('helpdesk.low')}</option>
                <option value="medium">{t('helpdesk.medium')}</option>
                <option value="high">{t('helpdesk.high')}</option>
                <option value="urgent">{t('helpdesk.urgent')}</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-700 mb-1">
              Tavsif (Muammoni batafsil tushuntiring)
            </label>
            <textarea
              required
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Muammo qachon boshlandi, qanday xatolik ko'rsatmoqda..."
              className="w-full rounded-lg border border-surface-300 p-2.5 text-xs text-surface-900 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-700 mb-1">
              Bog'liq Qurilma ID (ixtiyoriy)
            </label>
            <input
              type="number"
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              placeholder="Masalan: 1"
              className="w-full rounded-lg border border-surface-300 px-3 py-2 text-xs focus:border-brand-500 focus:outline-none"
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
              disabled={createMutation.isPending}
              className="rounded-lg bg-brand-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-brand-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Yuborilmoqda...' : t('helpdesk.newTicket')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
