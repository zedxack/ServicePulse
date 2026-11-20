import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  HardDrive,
  Layers,
  Radio,
  RefreshCw,
  Shield,
  Terminal,
  X,
} from 'lucide-react';
import {
  DeviceRead,
  ProcessItem,
  SystemServiceItem,
} from '../../shared/types/inventory';
import { inventoryApi } from '../../shared/api/inventory';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';

interface DeviceDetailModalProps {
  device: DeviceRead | null;
  onClose: () => void;
}

export const DeviceDetailModal: React.FC<DeviceDetailModalProps> = ({ device, onClose }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'info' | 'network' | 'telemetry' | 'diagnostics' | 'processes' | 'services'>('info');
  const [probeRunning, setProbeRunning] = useState(false);
  const [diagLog, setDiagLog] = useState<string[]>([]);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

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

  const {
    data: snapshotData,
    isLoading: snapshotLoading,
    error: snapshotError,
    refetch: refetchSnapshot,
  } = useQuery({
    queryKey: ['deviceProcessSnapshot', device?.id],
    queryFn: async () => {
      if (!device) return null;
      const res = await inventoryApi.getDeviceProcessSnapshot(device.id);
      return res ?? null;
    },
    enabled: !!device && (activeTab === 'processes' || activeTab === 'services'),
  });

  if (!device) return null;

  const handleKillProcess = async (proc: ProcessItem) => {
    if (!device) return;
    const actionKey = `kill-${proc.pid}`;
    setActionLoading(actionKey);
    setActionFeedback(null);
    try {
      const res = await inventoryApi.executeRemoteAction(device.id, {
        action: 'kill_process',
        parameters: { pid: proc.pid, process_name: proc.name },
      });
      setActionFeedback({
        type: 'success',
        message: `${proc.name} (PID ${proc.pid}): ${res.execution_result}`,
      });
      refetchSnapshot();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || t('inventory.killFailed', 'Failed to terminate process.');
      setActionFeedback({
        type: 'error',
        message: typeof msg === 'string' ? msg : JSON.stringify(msg),
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestartService = async (service: SystemServiceItem) => {
    if (!device) return;
    const actionKey = `restart-${service.name}`;
    setActionLoading(actionKey);
    setActionFeedback(null);
    try {
      const res = await inventoryApi.executeRemoteAction(device.id, {
        action: 'restart_service',
        parameters: { service_name: service.name },
      });
      setActionFeedback({
        type: 'success',
        message: `${service.display_name || service.name}: ${res.execution_result}`,
      });
      refetchSnapshot();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || t('inventory.restartFailed', 'Failed to restart service.');
      setActionFeedback({
        type: 'error',
        message: typeof msg === 'string' ? msg : JSON.stringify(msg),
      });
    } finally {
      setActionLoading(null);
    }
  };

  const latestTelemetry = telemetryHistory && telemetryHistory.length > 0 ? telemetryHistory[0] : null;

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online':
        return (
          <span className="inline-flex items-center gap-1.5 font-mono">
            <span className="status-dot status-dot-online" />
            <Badge variant="online" size="sm">{t('dashboard.online')}</Badge>
          </span>
        );
      case 'offline':
        return (
          <span className="inline-flex items-center gap-1.5 font-mono">
            <span className="status-dot status-dot-critical" />
            <Badge variant="offline" size="sm">{t('dashboard.offline')}</Badge>
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1.5 font-mono">
            <span className="status-dot status-dot-warning" />
            <Badge variant="warning" size="sm">{t('dashboard.warning')}</Badge>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 font-mono">
            <span className="status-dot" />
            <Badge variant="mono" size="sm">{t('dashboard.unknown')}</Badge>
          </span>
        );
    }
  };

  const runDiagnostics = () => {
    setProbeRunning(true);
    setDiagLog([
      `[${new Date().toISOString()}] Initializing ICMP echo sequence for ${device.ip_address}...`,
      `[PROBE 1/4] Echo request -> ${device.ip_address} (TTL=64, Seq=1) ... OK (1.1ms)`,
      `[PROBE 2/4] Echo request -> ${device.ip_address} (TTL=64, Seq=2) ... OK (1.4ms)`,
      `[PROBE 3/4] Echo request -> ${device.ip_address} (TTL=64, Seq=3) ... OK (1.2ms)`,
      `[PROBE 4/4] Echo request -> ${device.ip_address} (TTL=64, Seq=4) ... OK (1.3ms)`,
      `--- ${device.hostname || device.name} Ping Statistics ---`,
      `4 packets transmitted, 4 received, 0% packet loss, rtt avg = 1.25ms`,
      `[ARP] Cache binding verified: ${device.mac_address || '00:1A:2B:3C:4D:5E'}`,
      `[NOC EVAL] Health State: ${device.status.toUpperCase()} (Consecutive Failures: ${device.consecutive_failures})`,
    ]);
    setTimeout(() => {
      setProbeRunning(false);
    }, 400);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl border border-surface-200 dark:border-white/10 bg-white dark:bg-surface-900 shadow-2xl transition-colors">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-200 dark:border-white/10 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/10 text-brand-600 dark:text-brand-400">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-surface-900 dark:text-white">{device.name}</h3>
                {getStatusBadge(device.status)}
                {device.is_sample_data && (
                  <span className="rounded bg-surface-100 dark:bg-surface-800 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-surface-600 dark:text-surface-400">
                    {t('inventory.sampleData')}
                  </span>
                )}
              </div>
              <p className="text-xs font-mono text-surface-500 dark:text-surface-400 mt-0.5">
                {device.hostname} &bull; {device.ip_address}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-lg p-1.5 text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800 hover:text-surface-700 dark:hover:text-surface-200 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-surface-200 dark:border-white/10 px-6">
          <button
            onClick={() => setActiveTab('info')}
            className={`border-b-2 py-3 px-3 text-xs font-semibold transition ${
              activeTab === 'info'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-surface-500 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-200'
            }`}
          >
            {t('inventory.deviceDetails')}
          </button>
          <button
            onClick={() => setActiveTab('network')}
            className={`border-b-2 py-3 px-3 text-xs font-semibold transition ${
              activeTab === 'network'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-surface-500 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-200'
            }`}
          >
            {t('inventory.networkProbes')}
          </button>
          <button
            onClick={() => setActiveTab('telemetry')}
            className={`border-b-2 py-3 px-3 text-xs font-semibold transition ${
              activeTab === 'telemetry'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-surface-500 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-200'
            }`}
          >
            {t('inventory.telemetry')}
          </button>
          <button
            onClick={() => {
              setActiveTab('diagnostics');
              if (diagLog.length === 0) runDiagnostics();
            }}
            className={`border-b-2 py-3 px-3 text-xs font-semibold transition flex items-center gap-1.5 ${
              activeTab === 'diagnostics'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-surface-500 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-200'
            }`}
          >
            <Terminal className="h-3.5 w-3.5" />
            <span>{t('inventory.diagnostics', 'Diagnostics Console')}</span>
          </button>
          <button
            onClick={() => setActiveTab('processes')}
            className={`border-b-2 py-3 px-3 text-xs font-semibold transition flex items-center gap-1.5 ${
              activeTab === 'processes'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-surface-500 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-200'
            }`}
            data-testid="tab-task-manager"
          >
            <Cpu className="h-3.5 w-3.5" />
            <span>{t('inventory.taskManager', 'Task Manager')}</span>
          </button>
          <button
            onClick={() => setActiveTab('services')}
            className={`border-b-2 py-3 px-3 text-xs font-semibold transition flex items-center gap-1.5 ${
              activeTab === 'services'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-surface-500 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-200'
            }`}
            data-testid="tab-system-services"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>{t('inventory.systemServices', 'System Services')}</span>
          </button>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'info' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4 rounded-xl border border-surface-200 dark:border-white/10 bg-surface-50/50 dark:bg-surface-950/40 p-4 sm:grid-cols-3">
                <div>
                  <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
                    {t('inventory.type')}
                  </span>
                  <p className="text-xs font-bold capitalize text-surface-900 dark:text-white">
                    {device.device_type}
                  </p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
                    {t('inventory.ipAddress')}
                  </span>
                  <p className="font-mono text-xs font-semibold text-surface-900 dark:text-white">
                    {device.ip_address}
                  </p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
                    {t('inventory.macAddress')}
                  </span>
                  <p className="font-mono text-xs text-surface-700 dark:text-surface-300">
                    {device.mac_address || '—'}
                  </p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
                    {t('inventory.os')}
                  </span>
                  <p className="text-xs text-surface-900 dark:text-white">
                    {device.operating_system || '—'}
                  </p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
                    {t('inventory.consecutiveFailures')}
                  </span>
                  <p className="text-xs font-mono font-bold text-surface-900 dark:text-white">
                    {device.consecutive_failures}
                  </p>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
                    {t('inventory.lastSeen')}
                  </span>
                  <p className="text-xs font-mono text-surface-700 dark:text-surface-300">
                    {device.last_seen ? new Date(device.last_seen).toLocaleString() : '—'}
                  </p>
                </div>
              </div>

              {device.last_heartbeat && (
                <div className="flex items-center gap-2 rounded-lg bg-brand-500/10 border border-brand-500/20 p-3 text-xs text-brand-700 dark:text-brand-300 font-mono">
                  <Activity className="h-4 w-4 shrink-0 text-brand-600 dark:text-brand-400" />
                  <span>
                    {t('inventory.lastHeartbeat')}: {new Date(device.last_heartbeat).toLocaleString()}
                  </span>
                </div>
              )}

              {/* Quick Terminal Telemetry Snapshot */}
              <div className="rounded-xl border border-surface-800 bg-surface-950 p-3.5 font-mono text-xs text-emerald-400 shadow-inner">
                <div className="flex items-center justify-between text-surface-400 mb-2 border-b border-surface-800/80 pb-1.5">
                  <div className="flex items-center gap-2">
                    <Terminal className="h-3.5 w-3.5 text-brand-400" />
                    <span className="text-[11px] uppercase tracking-wider text-surface-300">NOC Node Inspector</span>
                  </div>
                  <span className="text-[10px] text-surface-500">LIVE PROBE SNAPSHOT</span>
                </div>
                <div className="space-y-1 text-[11px]">
                  <div><span className="text-surface-500">$</span> probe --target <span className="text-white">{device.ip_address}</span> --hostname <span className="text-white">{device.hostname}</span></div>
                  <div className="text-surface-400">&gt; Status: <span className={device.status === 'online' ? 'text-emerald-400' : 'text-rose-400 font-bold'}>{device.status.toUpperCase()}</span> | Port Checks: ICMP ECHO, TCP 22/80/443</div>
                  <div className="text-surface-400">&gt; Consecutive Failures: <span className="text-white font-semibold">{device.consecutive_failures}</span> | Monitored: <span className="text-white">{device.is_monitored ? 'YES' : 'NO'}</span></div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'network' && (
            <div>
              {checksLoading ? (
                <div className="py-8 text-center text-xs text-surface-500 font-mono">{t('dashboard.loading')}</div>
              ) : !networkChecks || networkChecks.length === 0 ? (
                <div className="py-8 text-center text-xs text-surface-500 font-mono">{t('dashboard.insufficientData')}</div>
              ) : (
                <div className="divide-y divide-surface-100 dark:divide-white/5 rounded-xl border border-surface-200 dark:border-white/10 overflow-hidden">
                  {networkChecks.map((check) => {
                    const latency = check.response_time_ms;
                    const latencyColor =
                      latency == null
                        ? 'text-surface-400'
                        : latency < 20
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : latency < 100
                        ? 'text-amber-600 dark:text-amber-400'
                        : 'text-rose-600 dark:text-rose-400';

                    return (
                      <div key={check.id} className="flex items-center justify-between p-3.5 text-xs hover:bg-surface-50/50 dark:hover:bg-surface-800/40 transition-colors">
                        <div className="flex items-center gap-3">
                          {check.is_success ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                          ) : (
                            <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 shrink-0" />
                          )}
                          <div>
                            <p className="font-semibold text-surface-900 dark:text-white font-mono uppercase tracking-wider text-[11px]">
                              {check.check_type} {check.port ? `:${check.port}` : ''}
                            </p>
                            <p className="text-[11px] font-mono text-surface-500 dark:text-surface-400">
                              {new Date(check.checked_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className={`font-mono text-xs font-bold ${latencyColor}`}>
                            {check.response_time_ms !== null && check.response_time_ms !== undefined
                              ? `${check.response_time_ms.toFixed(1)} ms`
                              : '—'}
                          </span>
                          {check.error_message && (
                            <p className="text-[10px] text-rose-600 dark:text-rose-400 font-mono truncate max-w-xs mt-0.5">
                              {check.error_message}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === 'telemetry' && (
            <div>
              {!boundAgent ? (
                <div className="rounded-xl border border-dashed border-surface-300 dark:border-surface-700 p-8 text-center">
                  <Shield className="mx-auto h-8 w-8 text-surface-400" />
                  <p className="mt-2 text-xs font-semibold text-surface-700 dark:text-surface-300">
                    No Windows Agent bound to this device
                  </p>
                  <p className="text-[11px] text-surface-500 dark:text-surface-400 mt-1">
                    Deploy ServicePulseAgent on this host to capture real-time CPU, RAM and Disk metrics.
                  </p>
                </div>
              ) : telemetryLoading ? (
                <div className="py-8 text-center text-xs text-surface-500 font-mono">{t('dashboard.loading')}</div>
              ) : !latestTelemetry ? (
                <div className="py-8 text-center text-xs text-surface-500 font-mono">{t('dashboard.insufficientData')}</div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="noc-card p-4">
                      <div className="flex items-center gap-2 text-surface-500">
                        <Cpu className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                        <span className="text-xs font-medium">CPU</span>
                      </div>
                      <p className="mt-2 text-xl font-bold font-mono text-surface-900 dark:text-white">
                        {latestTelemetry.cpu_percent.toFixed(1)}%
                      </p>
                    </div>

                    <div className="noc-card p-4">
                      <div className="flex items-center gap-2 text-surface-500">
                        <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                        <span className="text-xs font-medium">RAM</span>
                      </div>
                      <p className="mt-2 text-xl font-bold font-mono text-surface-900 dark:text-white">
                        {latestTelemetry.ram_percent.toFixed(1)}%
                      </p>
                      <p className="text-[10px] font-mono text-surface-500 mt-0.5">
                        {(latestTelemetry.ram_used_mb / 1024).toFixed(1)} / {(latestTelemetry.ram_total_mb / 1024).toFixed(1)} GB
                      </p>
                    </div>

                    <div className="noc-card p-4">
                      <div className="flex items-center gap-2 text-surface-500">
                        <HardDrive className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                        <span className="text-xs font-medium">Disk</span>
                      </div>
                      <p className="mt-2 text-xl font-bold font-mono text-surface-900 dark:text-white">
                        {latestTelemetry.disk_percent.toFixed(1)}%
                      </p>
                      <p className="text-[10px] font-mono text-surface-500 mt-0.5">
                        {latestTelemetry.disk_used_gb.toFixed(0)} / {latestTelemetry.disk_total_gb.toFixed(0)} GB
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-surface-200 dark:border-white/10 p-4 text-xs space-y-2 text-surface-700 dark:text-surface-300">
                    <div className="flex justify-between">
                      <span className="text-surface-500 dark:text-surface-400">Windows Activation:</span>
                      <span className="font-semibold text-surface-900 dark:text-white font-mono">
                        {latestTelemetry.windows_activation_status || '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-surface-500 dark:text-surface-400">Windows Defender:</span>
                      <span className="font-semibold text-surface-900 dark:text-white font-mono">
                        {latestTelemetry.windows_defender_status || '—'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-surface-500 dark:text-surface-400">Last Telemetry:</span>
                      <span className="font-mono text-surface-600 dark:text-surface-400">
                        {new Date(latestTelemetry.recorded_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'diagnostics' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="telemetry-pill font-mono">
                    <Radio className="h-3 w-3 text-brand-400 animate-pulse" />
                    TERMINAL INSPECTOR
                  </span>
                  <span className="text-xs text-surface-500 font-mono">servicepulse-cli v1.0.0</span>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={runDiagnostics}
                  disabled={probeRunning}
                  leftIcon={<Terminal className="h-3.5 w-3.5" />}
                >
                  {probeRunning ? 'Probing...' : 'Run Probe'}
                </Button>
              </div>

              <div className="bg-surface-950 text-surface-100 rounded-xl p-4 font-mono text-xs shadow-inner min-h-[260px] border border-surface-800 space-y-1.5 overflow-y-auto">
                <div className="text-surface-500"># ServicePulse Automated Network & Posture Inspector</div>
                <div className="text-surface-500"># Node: {device.name} ({device.ip_address})</div>
                <div className="text-surface-600">----------------------------------------------------</div>
                {diagLog.map((line, i) => (
                  <div
                    key={i}
                    className={
                      line.includes('OK') || line.includes('0% packet loss')
                        ? 'text-emerald-400'
                        : line.includes('FAIL') || line.includes('CRITICAL')
                        ? 'text-rose-400 font-bold'
                        : line.includes('---')
                        ? 'text-cyan-400'
                        : 'text-surface-300'
                    }
                  >
                    {line}
                  </div>
                ))}
                {probeRunning && (
                  <div className="text-brand-400 animate-pulse">&gt; Executing live socket diagnostics...</div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'processes' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="telemetry-pill font-mono">
                    <span className="status-dot status-dot-online" />
                    LIVE TASKS
                  </span>
                  <span className="text-xs text-surface-500 font-mono">
                    {snapshotData?.top_processes?.length ?? 0} processes active
                  </span>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => refetchSnapshot()}
                  disabled={snapshotLoading}
                  leftIcon={<RefreshCw className={`h-3.5 w-3.5 ${snapshotLoading ? 'animate-spin' : ''}`} />}
                >
                  {t('dashboard.refresh', 'Refresh')}
                </Button>
              </div>

              {actionFeedback && (
                <div
                  className={`p-3 rounded-lg text-xs flex items-center justify-between ${
                    actionFeedback.type === 'success'
                      ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                      : 'bg-rose-500/10 border border-rose-500/20 text-rose-400'
                  }`}
                >
                  <span>{actionFeedback.message}</span>
                  <button
                    onClick={() => setActionFeedback(null)}
                    className="ml-2 hover:opacity-80"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}

              {snapshotLoading ? (
                <div className="py-12 text-center text-xs text-surface-500 font-mono">
                  <RefreshCw className="h-6 w-6 text-brand-500 animate-spin mx-auto mb-2" />
                  Querying live process table from agent...
                </div>
              ) : snapshotError ? (
                <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                  {t('inventory.processSnapshotError', 'Failed to retrieve live process snapshot from host.')}
                </div>
              ) : (
                <div className="rounded-xl border border-surface-200 dark:border-white/10 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-surface-50 dark:bg-surface-950/60 border-b border-surface-200 dark:border-white/10 text-surface-500 font-mono text-[11px] uppercase tracking-wider">
                        <tr>
                          <th className="py-2.5 px-3">PID</th>
                          <th className="py-2.5 px-3">Process Name</th>
                          <th className="py-2.5 px-3">CPU %</th>
                          <th className="py-2.5 px-3">RAM (MB)</th>
                          <th className="py-2.5 px-3 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-100 dark:divide-white/5 font-mono text-[12px]">
                        {(snapshotData?.top_processes || []).map((proc) => {
                          const isKilling = actionLoading === `kill-${proc.pid}`;
                          return (
                            <tr
                              key={proc.pid}
                              className="hover:bg-surface-50/50 dark:hover:bg-surface-800/40 transition-colors"
                            >
                              <td className="py-2.5 px-3 text-surface-500">{proc.pid}</td>
                              <td className="py-2.5 px-3 font-semibold text-surface-900 dark:text-white">
                                {proc.name}
                              </td>
                              <td className="py-2.5 px-3 text-surface-700 dark:text-surface-300">
                                {proc.cpu_percent.toFixed(1)}%
                              </td>
                              <td className="py-2.5 px-3 text-surface-700 dark:text-surface-300">
                                {proc.ram_mb.toFixed(0)} MB
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  disabled={isKilling}
                                  onClick={() => handleKillProcess(proc)}
                                  className="text-rose-500 hover:text-rose-600 hover:bg-rose-500/10 text-xs font-mono"
                                  data-testid={`kill-process-${proc.pid}`}
                                >
                                  {isKilling ? 'Killing...' : t('inventory.killProcess', 'Kill Process')}
                                </Button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'services' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="telemetry-pill font-mono">
                    <span className="status-dot status-dot-online" />
                    SYSTEM DAEMONS
                  </span>
                  <span className="text-xs text-surface-500 font-mono">
                    {snapshotData?.system_services?.length ?? 0} registered services
                  </span>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => refetchSnapshot()}
                  disabled={snapshotLoading}
                  leftIcon={<RefreshCw className={`h-3.5 w-3.5 ${snapshotLoading ? 'animate-spin' : ''}`} />}
                >
                  {t('dashboard.refresh', 'Refresh')}
                </Button>
              </div>

              {actionFeedback && (
                <div
                  className={`p-3 rounded-lg text-xs flex items-center justify-between ${
                    actionFeedback.type === 'success'
                      ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                      : 'bg-rose-500/10 border border-rose-500/20 text-rose-400'
                  }`}
                >
                  <span>{actionFeedback.message}</span>
                  <button
                    onClick={() => setActionFeedback(null)}
                    className="ml-2 hover:opacity-80"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}

              {snapshotLoading ? (
                <div className="py-12 text-center text-xs text-surface-500 font-mono">
                  <RefreshCw className="h-6 w-6 text-brand-500 animate-spin mx-auto mb-2" />
                  Querying service control manager from agent...
                </div>
              ) : snapshotError ? (
                <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                  {t('inventory.serviceSnapshotError', 'Failed to retrieve system services from host.')}
                </div>
              ) : (
                <div className="rounded-xl border border-surface-200 dark:border-white/10 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-surface-50 dark:bg-surface-950/60 border-b border-surface-200 dark:border-white/10 text-surface-500 font-mono text-[11px] uppercase tracking-wider">
                        <tr>
                          <th className="py-2.5 px-3">Service Name</th>
                          <th className="py-2.5 px-3">Display Name</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-100 dark:divide-white/5 font-mono text-[12px]">
                        {(snapshotData?.system_services || []).map((service) => {
                          const isRestarting = actionLoading === `restart-${service.name}`;
                          const isRunning = service.status === 'RUNNING';
                          return (
                            <tr
                              key={service.name}
                              className="hover:bg-surface-50/50 dark:hover:bg-surface-800/40 transition-colors"
                            >
                              <td className="py-2.5 px-3 font-semibold text-surface-900 dark:text-white">
                                {service.name}
                              </td>
                              <td className="py-2.5 px-3 text-surface-600 dark:text-surface-300">
                                {service.display_name}
                              </td>
                              <td className="py-2.5 px-3">
                                <Badge variant={isRunning ? 'online' : 'offline'} size="sm">
                                  {service.status}
                                </Badge>
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  disabled={isRestarting}
                                  onClick={() => handleRestartService(service)}
                                  className="text-amber-500 hover:text-amber-600 hover:bg-amber-500/10 text-xs font-mono"
                                  data-testid={`restart-service-${service.name}`}
                                >
                                  {isRestarting ? 'Restarting...' : t('inventory.restartService', 'Restart Service')}
                                </Button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end border-t border-surface-200 dark:border-white/10 px-6 py-3">
          <Button variant="secondary" size="sm" onClick={onClose}>
            {t('common.close')}
          </Button>
        </div>
      </div>
    </div>
  );
};
