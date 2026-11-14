import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  HardDrive,
  Shield,
  X,
} from 'lucide-react';
import { DeviceRead } from '../../shared/types/inventory';
import { inventoryApi } from '../../shared/api/inventory';

interface DeviceDetailModalProps {
  device: DeviceRead | null;
  onClose: () => void;
}

export const DeviceDetailModal: React.FC<DeviceDetailModalProps> = ({ device, onClose }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'info' | 'network' | 'telemetry'>('info');

  const { data: networkChecks, isLoading: checksLoading } = useQuery({
    queryKey: ['deviceNetworkChecks', device?.id],
    queryFn: () => (device ? inventoryApi.getDeviceNetworkChecks(device.id, { limit: 20 }) : []),
    enabled: !!device && activeTab === 'network',
  });

  const { data: agents } = useQuery({
    queryKey: ['agentsList'],
    queryFn: () => inventoryApi.listAgents(),
    enabled: !!device && activeTab === 'telemetry',
  });

  const boundAgent = agents?.find((a) => a.device_id === device?.id);

  const { data: telemetryHistory, isLoading: telemetryLoading } = useQuery({
    queryKey: ['agentTelemetry', boundAgent?.id],
    queryFn: () => (boundAgent ? inventoryApi.getAgentTelemetry(boundAgent.id, { limit: 5 }) : []),
    enabled: !!boundAgent && activeTab === 'telemetry',
  });

  if (!device) return null;

  const latestTelemetry = telemetryHistory && telemetryHistory.length > 0 ? telemetryHistory[0] : null;

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t('dashboard.online')}
          </span>
        );
      case 'offline':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-700 ring-1 ring-rose-200">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            {t('dashboard.offline')}
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 ring-1 ring-amber-200">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {t('dashboard.warning')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2.5 py-0.5 text-xs font-semibold text-surface-700 ring-1 ring-surface-300">
            <span className="h-1.5 w-1.5 rounded-full bg-surface-400" />
            {t('dashboard.unknown')}
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
      <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-surface-900">{device.name}</h3>
                {getStatusBadge(device.status)}
                {device.is_sample_data && (
                  <span className="rounded bg-surface-100 px-1.5 py-0.5 text-[10px] font-semibold text-surface-600">
                    {t('inventory.sampleData')}
                  </span>
                )}
              </div>
              <p className="text-xs text-surface-500">
                {device.hostname} &bull; {device.ip_address}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 hover:text-surface-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-surface-200 px-6">
          <button
            onClick={() => setActiveTab('info')}
            className={`border-b-2 py-3 px-3 text-xs font-semibold transition ${
              activeTab === 'info'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-surface-500 hover:text-surface-800'
            }`}
          >
            {t('inventory.deviceDetails')}
          </button>
          <button
            onClick={() => setActiveTab('network')}
            className={`border-b-2 py-3 px-3 text-xs font-semibold transition ${
              activeTab === 'network'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-surface-500 hover:text-surface-800'
            }`}
          >
            {t('inventory.networkProbes')}
          </button>
          <button
            onClick={() => setActiveTab('telemetry')}
            className={`border-b-2 py-3 px-3 text-xs font-semibold transition ${
              activeTab === 'telemetry'
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-surface-500 hover:text-surface-800'
            }`}
          >
            {t('inventory.telemetry')}
          </button>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'info' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4 rounded-xl border border-surface-200 bg-surface-50/50 p-4 sm:grid-cols-3">
                <div>
                  <span className="text-[11px] font-medium text-surface-500">{t('inventory.type')}</span>
                  <p className="text-xs font-bold capitalize text-surface-900">{device.device_type}</p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500">{t('inventory.ipAddress')}</span>
                  <p className="font-mono text-xs font-semibold text-surface-900">{device.ip_address}</p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500">{t('inventory.macAddress')}</span>
                  <p className="font-mono text-xs text-surface-700">{device.mac_address || '—'}</p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500">{t('inventory.os')}</span>
                  <p className="text-xs text-surface-900">{device.operating_system || '—'}</p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500">{t('inventory.consecutiveFailures')}</span>
                  <p className="text-xs font-bold text-surface-900">{device.consecutive_failures}</p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500">{t('inventory.lastSeen')}</span>
                  <p className="text-xs text-surface-700">
                    {device.last_seen ? new Date(device.last_seen).toLocaleString() : '—'}
                  </p>
                </div>
              </div>

              {device.last_heartbeat && (
                <div className="flex items-center gap-2 rounded-lg bg-brand-50/70 p-3 text-xs text-brand-800">
                  <Activity className="h-4 w-4 shrink-0 text-brand-600" />
                  <span>
                    {t('inventory.lastHeartbeat')}: {new Date(device.last_heartbeat).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          )}

          {activeTab === 'network' && (
            <div>
              {checksLoading ? (
                <div className="py-8 text-center text-xs text-surface-500">{t('dashboard.loading')}</div>
              ) : !networkChecks || networkChecks.length === 0 ? (
                <div className="py-8 text-center text-xs text-surface-500">{t('dashboard.insufficientData')}</div>
              ) : (
                <div className="divide-y divide-surface-100 rounded-xl border border-surface-200">
                  {networkChecks.map((check) => (
                    <div key={check.id} className="flex items-center justify-between p-3 text-xs">
                      <div className="flex items-center gap-3">
                        {check.is_success ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-rose-600" />
                        )}
                        <div>
                          <p className="font-semibold text-surface-900 uppercase tracking-wider text-[11px]">
                            {check.check_type} {check.port ? `:${check.port}` : ''}
                          </p>
                          <p className="text-[11px] text-surface-500">{new Date(check.checked_at).toLocaleString()}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="font-mono text-xs font-bold text-surface-800">
                          {check.response_time_ms !== null && check.response_time_ms !== undefined
                            ? `${check.response_time_ms.toFixed(1)} ms`
                            : '—'}
                        </span>
                        {check.error_message && (
                          <p className="text-[10px] text-rose-600 truncate max-w-xs">{check.error_message}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'telemetry' && (
            <div>
              {!boundAgent ? (
                <div className="rounded-xl border border-dashed border-surface-300 p-8 text-center">
                  <Shield className="mx-auto h-8 w-8 text-surface-400" />
                  <p className="mt-2 text-xs font-semibold text-surface-700">
                    No Windows Agent bound to this device
                  </p>
                  <p className="text-[11px] text-surface-500">
                    Deploy ServicePulseAgent on this host to capture real-time CPU, RAM and Disk metrics.
                  </p>
                </div>
              ) : telemetryLoading ? (
                <div className="py-8 text-center text-xs text-surface-500">{t('dashboard.loading')}</div>
              ) : !latestTelemetry ? (
                <div className="py-8 text-center text-xs text-surface-500">{t('dashboard.insufficientData')}</div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="rounded-xl border border-surface-200 bg-surface-50 p-4">
                      <div className="flex items-center gap-2 text-surface-500">
                        <Cpu className="h-4 w-4 text-brand-600" />
                        <span className="text-xs font-medium">CPU</span>
                      </div>
                      <p className="mt-2 text-xl font-bold text-surface-900">
                        {latestTelemetry.cpu_percent.toFixed(1)}%
                      </p>
                    </div>

                    <div className="rounded-xl border border-surface-200 bg-surface-50 p-4">
                      <div className="flex items-center gap-2 text-surface-500">
                        <Activity className="h-4 w-4 text-emerald-600" />
                        <span className="text-xs font-medium">RAM</span>
                      </div>
                      <p className="mt-2 text-xl font-bold text-surface-900">
                        {latestTelemetry.ram_percent.toFixed(1)}%
                      </p>
                      <p className="text-[10px] text-surface-500">
                        {(latestTelemetry.ram_used_mb / 1024).toFixed(1)} / {(latestTelemetry.ram_total_mb / 1024).toFixed(1)} GB
                      </p>
                    </div>

                    <div className="rounded-xl border border-surface-200 bg-surface-50 p-4">
                      <div className="flex items-center gap-2 text-surface-500">
                        <HardDrive className="h-4 w-4 text-amber-600" />
                        <span className="text-xs font-medium">Disk</span>
                      </div>
                      <p className="mt-2 text-xl font-bold text-surface-900">
                        {latestTelemetry.disk_percent.toFixed(1)}%
                      </p>
                      <p className="text-[10px] text-surface-500">
                        {latestTelemetry.disk_used_gb.toFixed(0)} / {latestTelemetry.disk_total_gb.toFixed(0)} GB
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-surface-200 p-4 text-xs space-y-2">
                    <div className="flex justify-between">
                      <span className="text-surface-500">Windows Activation:</span>
                      <span className="font-semibold text-surface-900">{latestTelemetry.windows_activation_status || '—'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-surface-500">Windows Defender:</span>
                      <span className="font-semibold text-surface-900">{latestTelemetry.windows_defender_status || '—'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-surface-500">Last Telemetry:</span>
                      <span className="text-surface-700">{new Date(latestTelemetry.recorded_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end border-t border-surface-200 px-6 py-3">
          <button
            onClick={onClose}
            className="rounded-lg bg-surface-100 px-4 py-2 text-xs font-semibold text-surface-700 hover:bg-surface-200"
          >
            Yopish
          </button>
        </div>
      </div>
    </div>
  );
};
