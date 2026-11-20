import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DownloadCloud, X } from 'lucide-react';
import { softwareApi } from '../../shared/api/software';
import { inventoryApi } from '../../shared/api/inventory';
import { Button } from '../../shared/components/Button';

interface RequestSoftwareModalProps {
  initialSoftwareName?: string;
  onClose: () => void;
}

export const RequestSoftwareModal: React.FC<RequestSoftwareModalProps> = ({
  initialSoftwareName = '',
  onClose,
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [softwareName, setSoftwareName] = useState(initialSoftwareName);
  const [version, setVersion] = useState('');
  const [deviceId, setDeviceId] = useState<number | ''>('');
  const [reason, setReason] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: catalog = [] } = useQuery({
    queryKey: ['softwareCatalog'],
    queryFn: softwareApi.getSoftwareCatalog,
  });

  const { data: devices = [] } = useQuery({
    queryKey: ['userDevicesForSoftware'],
    queryFn: () => inventoryApi.listDevices({ limit: 50 }),
  });

  const requestMutation = useMutation({
    mutationFn: () => {
      if (!deviceId) throw new Error('Please select a target device');
      return softwareApi.submitSoftwareRequest({
        device_id: Number(deviceId),
        software_name: softwareName,
        software_version: version.trim() || undefined,
        reason: reason.trim(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['softwareRequests'] });
      onClose();
    },
    onError: (err: unknown) => {
      const resMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      const errMsg = err instanceof Error ? err.message : undefined;
      setErrorMsg(resMsg || errMsg || 'Failed to submit software request');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!softwareName) {
      setErrorMsg('Please select a software package');
      return;
    }
    if (!deviceId) {
      setErrorMsg('Please select a target device');
      return;
    }
    if (reason.trim().length < 5) {
      setErrorMsg('Business justification must be at least 5 characters');
      return;
    }
    setErrorMsg(null);
    requestMutation.mutate();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div className="relative w-full max-w-lg rounded-2xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-2xl transition-colors">
        <div className="flex items-center justify-between border-b border-surface-200 dark:border-surface-800 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500/10 text-brand-600 dark:text-brand-400">
              <DownloadCloud className="h-4 w-4" />
            </div>
            <h3 className="text-base font-bold text-surface-900 dark:text-white">
              {t('softwareApproval.requestInstall')}
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
              {t('softwareApproval.selectSoftware')}
            </label>
            <select
              required
              value={softwareName}
              onChange={(e) => setSoftwareName(e.target.value)}
              className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
            >
              <option value="">-- Select Software Package --</option>
              {catalog.map((pkg) => (
                <option key={pkg} value={pkg}>
                  {pkg}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
              {t('softwareApproval.targetDevice')}
            </label>
            <select
              required
              value={deviceId}
              onChange={(e) => setDeviceId(Number(e.target.value))}
              className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
            >
              <option value="">-- Select Target Device --</option>
              {devices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.hostname} - {d.ip_address})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
              {t('softwareApproval.versionOptional')}
            </label>
            <input
              type="text"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="e.g. Latest or 1.84.0"
              className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
              {t('softwareApproval.reason')}
            </label>
            <textarea
              required
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t('softwareApproval.reasonPlaceholder')}
              className="w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 p-2.5 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" size="sm" onClick={onClose}>
              {t('incidents.cancel')}
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={requestMutation.isPending}>
              {requestMutation.isPending ? 'Submitting...' : t('softwareApproval.submitRequest')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
