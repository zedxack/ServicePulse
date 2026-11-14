/**
 * ServicePulse - Live Monitoring Dashboard
 * Author: Muhammadyusuf Usmonov
 * Academic Purpose: AT-Servis BMI
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Radio className="w-7 h-7 text-primary-600 animate-pulse" />
            {t('monitoring.live_title', 'Live Fleet Monitoring')}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t(
              'monitoring.live_subtitle',
              'Real-time WebSocket telemetry stream and operational event bus'
            )}
          </p>
        </div>

        {/* Connection status indicator */}
        <div className="flex items-center gap-3">
          <div
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
              status === 'connected'
                ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                : status === 'connecting'
                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
            }`}
          >
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                status === 'connected'
                  ? 'bg-green-500 animate-ping'
                  : status === 'connecting'
                  ? 'bg-amber-500 animate-pulse'
                  : 'bg-red-500'
              }`}
            />
            {status === 'connected' && t('monitoring.status_connected', 'Connected (Live)')}
            {status === 'connecting' && t('monitoring.status_connecting', 'Connecting...')}
            {status === 'disconnected' && t('monitoring.status_disconnected', 'Disconnected')}
            {status === 'error' && t('monitoring.status_error', 'Connection Error')}
          </div>

          <button
            onClick={() => {
              reconnect();
              refetchDevices();
            }}
            className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
            title={t('common.refresh', 'Refresh')}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI Counters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {devices.length}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('monitoring.total_devices', 'Monitored Devices')}
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-green-50 dark:bg-green-900/30 rounded-lg text-green-600 dark:text-green-400">
            <Wifi className="w-5 h-5" />
          </div>
          <div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {onlineCount}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('monitoring.online_devices', 'Online')}
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-red-50 dark:bg-red-900/30 rounded-lg text-red-600 dark:text-red-400">
            <WifiOff className="w-5 h-5" />
          </div>
          <div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {offlineCount}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('monitoring.offline_devices', 'Offline')}
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex items-center gap-3">
          <div className="p-3 bg-purple-50 dark:bg-purple-900/30 rounded-lg text-purple-600 dark:text-purple-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {events.length}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('monitoring.live_events', 'Buffered Events')}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab('telemetry')}
            className={`pb-3 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'telemetry'
                ? 'border-primary-600 text-primary-600 dark:border-primary-400 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            <Cpu className="w-4 h-4" />
            {t('monitoring.fleet_telemetry', 'Live Fleet Telemetry')} ({devices.length})
          </button>
          <button
            onClick={() => setActiveTab('events')}
            className={`pb-3 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'events'
                ? 'border-primary-600 text-primary-600 dark:border-primary-400 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            <Activity className="w-4 h-4" />
            {t('monitoring.live_event_bus', 'Live Event Stream')} ({events.length})
          </button>
        </div>

        {activeTab === 'events' && (
          <div className="flex items-center gap-2 pb-2">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium border ${
                isPaused
                  ? 'bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-900/30 dark:text-amber-300'
                  : 'bg-gray-100 text-gray-700 border-gray-300 dark:bg-gray-800 dark:text-gray-300'
              }`}
            >
              {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
              {isPaused ? t('monitoring.resume', 'Resume') : t('monitoring.pause', 'Pause')}
            </button>
            <button
              onClick={clearEvents}
              className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-medium text-gray-600 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <Trash2 className="w-3.5 h-3.5" />
              {t('common.clear', 'Clear')}
            </button>
          </div>
        )}
      </div>

      {/* Tab 1: Live Fleet Telemetry */}
      {activeTab === 'telemetry' && (
        <div className="space-y-4">
          {isDevicesLoading ? (
            <div className="p-8 text-center text-gray-500">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-primary-500" />
              {t('common.loading', 'Loading fleet devices...')}
            </div>
          ) : devices.length === 0 ? (
            <div className="p-12 text-center bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
              <Server className="w-12 h-12 mx-auto text-gray-400 mb-3" />
              <p className="text-gray-500 dark:text-gray-400">
                {t('monitoring.no_devices', 'No monitored devices found.')}
              </p>
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
                    className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm hover:border-primary-500 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                          <Server className="w-4 h-4 text-gray-500" />
                          {device.name}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {device.ip_address} &bull; {device.device_type}
                        </div>
                      </div>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                          device.status === 'online'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                            : device.status === 'warning'
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                            : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                        }`}
                      >
                        {device.status.toUpperCase()}
                      </span>
                    </div>

                    {/* Live Telemetry Progress Bars */}
                    <div className="space-y-3 pt-2 border-t border-gray-100 dark:border-gray-700 text-xs">
                      {/* CPU */}
                      <div>
                        <div className="flex justify-between text-gray-600 dark:text-gray-400 mb-1">
                          <span className="flex items-center gap-1">
                            <Cpu className="w-3.5 h-3.5" /> CPU
                          </span>
                          <span className="font-semibold">
                            {cpu !== null ? `${cpu.toFixed(1)}%` : '—'}
                          </span>
                        </div>
                        <div className="w-full bg-gray-100 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${
                              cpu && cpu > 85
                                ? 'bg-red-500'
                                : cpu && cpu > 70
                                ? 'bg-amber-500'
                                : 'bg-primary-600'
                            }`}
                            style={{ width: `${Math.min(cpu ?? 0, 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* RAM */}
                      <div>
                        <div className="flex justify-between text-gray-600 dark:text-gray-400 mb-1">
                          <span className="flex items-center gap-1">
                            <Activity className="w-3.5 h-3.5" /> RAM
                          </span>
                          <span className="font-semibold">
                            {ram !== null ? `${ram.toFixed(1)}%` : '—'}
                          </span>
                        </div>
                        <div className="w-full bg-gray-100 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${
                              ram && ram > 90
                                ? 'bg-red-500'
                                : ram && ram > 75
                                ? 'bg-amber-500'
                                : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(ram ?? 0, 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* Disk */}
                      <div>
                        <div className="flex justify-between text-gray-600 dark:text-gray-400 mb-1">
                          <span className="flex items-center gap-1">
                            <HardDrive className="w-3.5 h-3.5" /> Disk
                          </span>
                          <span className="font-semibold">
                            {disk !== null ? `${disk.toFixed(1)}%` : '—'}
                          </span>
                        </div>
                        <div className="w-full bg-gray-100 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-indigo-500 h-full transition-all duration-500"
                            style={{ width: `${Math.min(disk ?? 0, 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* Defender & Telemetry Timestamp */}
                      <div className="flex items-center justify-between pt-1 text-gray-500 dark:text-gray-400">
                        <span className="flex items-center gap-1">
                          <Shield className="w-3.5 h-3.5 text-blue-500" />
                          {defender || 'Defender'}
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
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  filterType === f.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Event Stream Log */}
          <div className="bg-gray-900 text-gray-100 rounded-xl p-4 font-mono text-xs shadow-inner min-h-[420px] max-h-[600px] overflow-y-auto space-y-2">
            {filteredEvents.length === 0 ? (
              <div className="text-gray-500 text-center py-16">
                <Activity className="w-8 h-8 mx-auto mb-2 text-gray-600 animate-pulse" />
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
                    className="p-2.5 rounded bg-gray-800/80 border border-gray-700/60 hover:border-gray-600 transition-colors"
                  >
                    <div className="flex items-center justify-between text-gray-400 mb-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            isIncident
                              ? 'bg-red-900/60 text-red-300 border border-red-700'
                              : isAlert
                              ? 'bg-amber-900/60 text-amber-300 border border-amber-700'
                              : isRemediation
                              ? 'bg-purple-900/60 text-purple-300 border border-purple-700'
                              : isStatus
                              ? 'bg-blue-900/60 text-blue-300 border border-blue-700'
                              : 'bg-gray-700 text-gray-300'
                          }`}
                        >
                          {ev.type}
                        </span>
                        <span className="text-gray-300 font-semibold">
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
                      <span className="text-gray-500">
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <pre className="text-gray-300 text-[11px] overflow-x-auto p-1 bg-black/40 rounded mt-1">
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
