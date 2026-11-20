/**
 * ServicePulse - Live Monitoring Dashboard
 * Author: Muhammadyusuf Usmonov
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  Cpu,
  HardDrive,
  Pause,
  Play,
  Radio,
  RefreshCw,
  Server,
  Shield,
  Trash2,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useRealtimeMonitoring } from './useRealtimeMonitoring';
import { inventoryApi } from '../../shared/api/inventory';
import { WSMessage } from '../../shared/types/ws';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { EmptyState } from '../../shared/components/EmptyState';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';
import { PulseIndicator } from '../../shared/components/PulseIndicator';

export const LiveMonitoringPage: React.FC = () => {
  const { t } = useTranslation();
  const { status, events, telemetryMap, clearEvents, reconnect } = useRealtimeMonitoring(true);

  const [activeTab, setActiveTab] = useState<'telemetry' | 'events'>('telemetry');
  const [filterType, setFilterType] = useState<string>('all');
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [displayedEvents, setDisplayedEvents] = useState<WSMessage[]>([]);

  // Keep a local frozen copy when paused
  React.useEffect(() => {
    if (!isPaused) {
      setDisplayedEvents(events);
    }
  }, [events, isPaused]);

  // Fetch devices
  const {
    data: devices = [],
    isLoading: isDevicesLoading,
    refetch: refetchDevices,
  } = useQuery({
    queryKey: ['devices'],
    queryFn: () => inventoryApi.listDevices({ limit: 100 }),
  });

  const onlineCount = devices.filter((d) => d.status === 'online').length;
  const offlineCount = devices.filter((d) => d.status === 'offline').length;

  const filteredEvents = displayedEvents.filter((ev) => {
    if (filterType === 'all') return true;
    if (filterType === 'incidents') return ev.type.startsWith('incident:');
    if (filterType === 'devices') return ev.type.startsWith('device:');
    if (filterType === 'alerts') return ev.type === 'alert:created';
    if (filterType === 'remediation') return ev.type === 'remediation:status';
    return ev.type === filterType;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <Radio className="h-6 w-6 text-brand-600 dark:text-brand-400 animate-pulse" />
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('monitoring.live_title', 'Live Fleet Monitoring')}
            </h1>
            <span className="telemetry-pill font-mono">
              <span className={`status-dot ${status === 'connected' ? 'status-dot-online' : 'status-dot-critical'}`} />
              REALTIME STREAM
            </span>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400 mt-0.5">
            {t(
              'monitoring.live_subtitle',
              'Real-time WebSocket telemetry stream and operational event bus'
            )}
          </p>
        </div>

        {/* Connection status indicator & refresh */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="inline-flex items-center gap-2 rounded-lg border border-surface-200 dark:border-white/10 bg-white dark:bg-surface-900 px-3 py-1.5 text-xs font-mono font-semibold shadow-2xs">
            <PulseIndicator
              status={
                status === 'connected'
                  ? 'online'
                  : status === 'connecting'
                  ? 'warning'
                  : 'offline'
              }
              size="sm"
            />
            <span className="text-surface-700 dark:text-surface-200">
              {status === 'connected' && t('monitoring.status_connected', 'Connected (Live)')}
              {status === 'connecting' && t('monitoring.status_connecting', 'Connecting...')}
              {status === 'disconnected' && t('monitoring.status_disconnected', 'Disconnected')}
              {status === 'error' && t('monitoring.status_error', 'Connection Error')}
            </span>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              reconnect();
              refetchDevices();
            }}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            {t('common.refresh', 'Refresh')}
          </Button>
        </div>
      </div>

      {/* KPI Counters */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          title={t('monitoring.total_devices', 'Monitored Devices')}
          value={devices.length}
          subtitle="Inventory endpoints"
          icon={<Server className="h-4 w-4" />}
          accentColor="brand"
          className="noc-card"
        />
        <MetricCard
          title={t('monitoring.online_devices', 'Online')}
          value={onlineCount}
          subtitle="Active pulse received"
          icon={<Wifi className="h-4 w-4" />}
          accentColor="emerald"
          className="noc-card"
        />
        <MetricCard
          title={t('monitoring.offline_devices', 'Offline')}
          value={offlineCount}
          subtitle="Heartbeat lost"
          icon={<WifiOff className="h-4 w-4" />}
          accentColor={offlineCount > 0 ? 'rose' : 'mono'}
          className="noc-card"
        />
        <MetricCard
          title={t('monitoring.live_events', 'Buffered Events')}
          value={events.length}
          subtitle="In-memory stream"
          icon={<Activity className="h-4 w-4" />}
          accentColor="purple"
          className="noc-card"
        />
      </div>

      {/* Tabs */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 dark:border-white/10 bg-white dark:bg-surface-900 p-3 shadow-xs transition-colors sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1 rounded-lg border border-surface-200 dark:border-white/10 bg-surface-50 dark:bg-surface-950/60 p-1 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('telemetry')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 transition ${
              activeTab === 'telemetry'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white'
            }`}
          >
            <Cpu className="h-3.5 w-3.5" />
            <span>{t('monitoring.fleet_telemetry', 'Live Fleet Telemetry')} ({devices.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('events')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 transition ${
              activeTab === 'events'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white'
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            <span>{t('monitoring.live_event_bus', 'Live Event Stream')} ({events.length})</span>
          </button>
        </div>

        {activeTab === 'events' && (
          <div className="flex items-center gap-2">
            <Button
              variant={isPaused ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setIsPaused(!isPaused)}
              leftIcon={isPaused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
            >
              {isPaused ? t('monitoring.resume', 'Resume') : t('monitoring.pause', 'Pause')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={clearEvents}
              leftIcon={<Trash2 className="h-3.5 w-3.5" />}
            >
              {t('common.clear', 'Clear')}
            </Button>
          </div>
        )}
      </div>

      {/* Tab 1: Live Fleet Telemetry */}
      {activeTab === 'telemetry' && (
        <div className="space-y-4">
          {isDevicesLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <LoadingSkeleton height="h-48" />
              <LoadingSkeleton height="h-48" />
              <LoadingSkeleton height="h-48" />
            </div>
          ) : devices.length === 0 ? (
            <div className="py-12">
              <EmptyState
                icon={<Server className="h-8 w-8" />}
                title={t('monitoring.no_devices', 'No monitored devices found.')}
                description="Add devices to your inventory to start streaming real-time telemetry."
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {devices.map((device) => {
                const liveTel = telemetryMap[device.id];
                const cpu = liveTel?.cpu_percent ?? null;
                const ram = liveTel?.ram_percent ?? null;
                const disk = liveTel?.disk_percent ?? null;
                const defender = liveTel?.windows_defender_status ?? null;

                return (
                  <div
                    key={device.id}
                    className="noc-card p-5 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="font-semibold text-surface-900 dark:text-white flex items-center gap-2">
                          <Server className="h-4 w-4 text-surface-400 shrink-0" />
                          <span>{device.name}</span>
                        </div>
                        <div className="text-xs font-mono text-surface-500 dark:text-surface-400 mt-0.5">
                          {device.ip_address} &bull; <span className="capitalize">{device.device_type}</span>
                        </div>
                      </div>
                      <span className="inline-flex items-center gap-1.5 font-mono">
                        <span
                          className={`status-dot ${
                            device.status === 'online'
                              ? 'status-dot-online'
                              : device.status === 'warning'
                              ? 'status-dot-warning'
                              : 'status-dot-critical'
                          }`}
                        />
                        <Badge
                          variant={
                            device.status === 'online'
                              ? 'online'
                              : device.status === 'warning'
                              ? 'warning'
                              : 'offline'
                          }
                          size="sm"
                        >
                          {device.status}
                        </Badge>
                      </span>
                    </div>

                    {/* Live Telemetry Progress Bars */}
                    <div className="space-y-3 pt-3 border-t border-surface-100 dark:border-white/5 text-xs">
                      {/* CPU */}
                      <div>
                        <div className="flex justify-between text-surface-600 dark:text-surface-400 mb-1">
                          <span className="flex items-center gap-1 font-medium">
                            <Cpu className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" /> CPU
                          </span>
                          <span className="font-mono font-bold text-surface-900 dark:text-white">
                            {cpu !== null ? `${cpu.toFixed(1)}%` : '—'}
                          </span>
                        </div>
                        <div className="w-full bg-surface-100 dark:bg-surface-800 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${
                              cpu && cpu >= 90
                                ? 'bg-rose-500'
                                : cpu && cpu >= 75
                                ? 'bg-amber-500'
                                : 'bg-brand-500'
                            }`}
                            style={{ width: `${Math.min(cpu ?? 0, 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* RAM */}
                      <div>
                        <div className="flex justify-between text-surface-600 dark:text-surface-400 mb-1">
                          <span className="flex items-center gap-1 font-medium">
                            <Activity className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" /> RAM
                          </span>
                          <span className="font-mono font-bold text-surface-900 dark:text-white">
                            {ram !== null ? `${ram.toFixed(1)}%` : '—'}
                          </span>
                        </div>
                        <div className="w-full bg-surface-100 dark:bg-surface-800 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${
                              ram && ram >= 90
                                ? 'bg-rose-500'
                                : ram && ram >= 75
                                ? 'bg-amber-500'
                                : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(ram ?? 0, 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* Disk */}
                      <div>
                        <div className="flex justify-between text-surface-600 dark:text-surface-400 mb-1">
                          <span className="flex items-center gap-1 font-medium">
                            <HardDrive className="h-3.5 w-3.5 text-slate-500 dark:text-slate-400" /> Disk
                          </span>
                          <span className="font-mono font-bold text-surface-900 dark:text-white">
                            {disk !== null ? `${disk.toFixed(1)}%` : '—'}
                          </span>
                        </div>
                        <div className="w-full bg-surface-100 dark:bg-surface-800 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-slate-500 dark:bg-slate-400 h-full transition-all duration-500"
                            style={{ width: `${Math.min(disk ?? 0, 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* Defender & Telemetry Timestamp */}
                      <div className="flex items-center justify-between pt-1 text-[11px] text-surface-500 dark:text-surface-400 font-mono">
                        <span className="flex items-center gap-1">
                          <Shield className="h-3.5 w-3.5 text-brand-500" />
                          <span>{defender || 'Defender'}</span>
                        </span>
                        <span>
                          {liveTel?.recorded_at
                            ? new Date(liveTel.recorded_at).toLocaleTimeString()
                            : device.last_seen
                            ? new Date(device.last_seen).toLocaleTimeString()
                            : 'No ping'}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Live Event Feed */}
      {activeTab === 'events' && (
        <div className="space-y-3">
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: 'all', label: t('monitoring.filter_all', 'All Events') },
              { id: 'devices', label: t('monitoring.filter_devices', 'Device Status') },
              { id: 'incidents', label: t('monitoring.filter_incidents', 'Incidents') },
              { id: 'alerts', label: t('monitoring.filter_alerts', 'In-App Alerts') },
              { id: 'remediation', label: t('monitoring.filter_remediation', 'Remediation') },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilterType(f.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-colors ${
                  filterType === f.id
                    ? 'bg-brand-600 text-white shadow-xs'
                    : 'bg-white dark:bg-surface-900 text-surface-700 dark:text-surface-300 border border-surface-200 dark:border-white/10 hover:bg-surface-50 dark:hover:bg-surface-800'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Event Stream Log */}
          <div className="bg-surface-950 text-surface-100 rounded-xl p-4 font-mono text-xs shadow-inner min-h-[420px] max-h-[600px] overflow-y-auto space-y-2 border border-surface-800">
            {filteredEvents.length === 0 ? (
              <div className="text-surface-500 text-center py-16">
                <Activity className="w-8 h-8 mx-auto mb-2 text-surface-600 animate-pulse" />
                {t('monitoring.awaiting_events', 'Listening for real-time WebSocket events...')}
              </div>
            ) : (
              filteredEvents.map((ev, idx) => {
                const isIncident = ev.type.startsWith('incident:');
                const isAlert = ev.type === 'alert:created';
                const isRemediation = ev.type === 'remediation:status';
                const isStatus = ev.type === 'device:status_change';

                return (
                  <div
                    key={`${ev.timestamp}-${idx}`}
                    className="p-3 rounded-lg bg-surface-900/90 border border-surface-800 hover:border-surface-700 transition-colors"
                  >
                    <div className="flex items-center justify-between text-surface-400 mb-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono uppercase tracking-wider ${
                            isIncident
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : isAlert
                              ? 'bg-amber-950 text-amber-300 border border-amber-800'
                              : isRemediation
                              ? 'bg-purple-950 text-purple-300 border border-purple-800'
                              : isStatus
                              ? 'bg-blue-950 text-blue-300 border border-blue-800'
                              : 'bg-surface-800 text-surface-300'
                          }`}
                        >
                          {ev.type}
                        </span>
                        <span className="text-surface-200 font-semibold font-mono">
                          {typeof ev.payload === 'object' && ev.payload !== null
                            ? String(
                                (ev.payload as Record<string, unknown>).title ||
                                  (ev.payload as Record<string, unknown>).device_name ||
                                  (ev.payload as Record<string, unknown>).action_name ||
                                  ev.type
                              )
                            : String(ev.payload)}
                        </span>
                      </div>
                      <span className="text-surface-500 text-[11px] font-mono">
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <pre className="text-surface-300 text-[11px] overflow-x-auto p-2 bg-black/50 rounded mt-1 border border-surface-800/60 font-mono">
                      {JSON.stringify(ev.payload, null, 2)}
                    </pre>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
