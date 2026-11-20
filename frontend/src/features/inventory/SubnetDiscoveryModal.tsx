import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  Camera,
  Check,
  CheckCircle2,
  Monitor,
  Network,
  RefreshCw,
  Server,
  Wifi,
  X,
} from 'lucide-react';
import { inventoryApi } from '../../shared/api/inventory';
import { SubnetDiscoveryResponse } from '../../shared/types/inventory';
import { Badge } from '../../shared/components/Badge';

interface SubnetDiscoveryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess?: () => void;
}

export const SubnetDiscoveryModal: React.FC<SubnetDiscoveryModalProps> = ({
  isOpen,
  onClose,
  onImportSuccess,
}) => {
  const { t } = useTranslation();
  const [subnetCidr, setSubnetCidr] = useState('192.168.10.0/24');
  const [scanMode, setScanMode] = useState<'fast' | 'deep'>('fast');
  const [scanning, setScanning] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [discoveryResult, setDiscoveryResult] = useState<SubnetDiscoveryResponse | null>(null);
  const [selectedIps, setSelectedIps] = useState<Set<string>>(new Set());
  const [importSuccessMsg, setImportSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleScan = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError(null);
    setImportSuccessMsg(null);
    setScanning(true);

    try {
      const res = await inventoryApi.discoverSubnet({
        subnet_cidr: subnetCidr.trim(),
        scan_mode: scanMode,
      });
      setDiscoveryResult(res);

      // Auto-select unregistered candidates by default
      const newIps = new Set<string>();
      res.candidates.forEach((c) => {
        if (!c.already_registered) {
          newIps.add(c.ip_address);
        }
      });
      setSelectedIps(newIps);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || t('inventory.scanFailed', 'Failed to scan subnet.');
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setScanning(false);
    }
  };

  const toggleSelectAll = () => {
    if (!discoveryResult) return;
    const unregistered = discoveryResult.candidates.filter((c) => !c.already_registered);
    if (selectedIps.size === unregistered.length) {
      setSelectedIps(new Set());
    } else {
      setSelectedIps(new Set(unregistered.map((c) => c.ip_address)));
    }
  };

  const toggleIp = (ip: string) => {
    const next = new Set(selectedIps);
    if (next.has(ip)) {
      next.delete(ip);
    } else {
      next.add(ip);
    }
    setSelectedIps(next);
  };

  const handleImport = async () => {
    if (!discoveryResult || selectedIps.size === 0) return;
    setImporting(true);
    setError(null);

    try {
      const candidatesToImport = discoveryResult.candidates
        .filter((c) => selectedIps.has(c.ip_address))
        .map((c) => ({
          ip_address: c.ip_address,
          hostname: c.hostname,
          mac_address: c.mac_address,
          device_type: c.detected_device_type,
        }));

      const res = await inventoryApi.importDiscovered({
        devices: candidatesToImport,
      });

      setImportSuccessMsg(
        res.message ||
          t('inventory.importSuccess', 'Successfully imported {{count}} devices into CMDB inventory.', {
            count: res.imported_count,
          })
      );

      // Mark imported candidates as already_registered
      setDiscoveryResult((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          candidates: prev.candidates.map((c) =>
            selectedIps.has(c.ip_address) ? { ...c, already_registered: true } : c
          ),
        };
      });
      setSelectedIps(new Set());

      if (onImportSuccess) {
        onImportSuccess();
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || t('inventory.importFailed', 'Failed to import nodes.');
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setImporting(false);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'server':
        return <Server className="h-3.5 w-3.5 text-brand-500" />;
      case 'router':
      case 'switch':
        return <Wifi className="h-3.5 w-3.5 text-emerald-500" />;
      case 'ip_camera':
        return <Camera className="h-3.5 w-3.5 text-amber-500" />;
      default:
        return <Monitor className="h-3.5 w-3.5 text-surface-400" />;
    }
  };

  const unregisteredCount =
    discoveryResult?.candidates.filter((c) => !c.already_registered).length || 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="noc-panel w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl border border-surface-200 bg-white shadow-2xl dark:border-white/10 dark:bg-surface-900">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-200 dark:border-white/10 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/10 text-brand-600 dark:text-brand-400">
              <Network className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-surface-900 dark:text-white">
                  {t('inventory.scanSubnetTitle', 'Subnet Auto-Discovery Scanner')}
                </h3>
                <span className="telemetry-pill font-mono">
                  <span className="status-dot status-dot-online" />
                  RMM AUTO-PROBE
                </span>
              </div>
              <p className="text-xs text-surface-500 dark:text-surface-400 mt-0.5">
                {t(
                  'inventory.scanSubnetSubtitle',
                  'Scan local or remote network subnets to detect active servers, routers, workstations, and IP cameras'
                )}
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

        {/* Scan Controls Strip */}
        <form onSubmit={handleScan} className="border-b border-surface-200 dark:border-white/10 bg-surface-50/50 dark:bg-surface-950/40 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 items-center gap-2">
              <div className="relative flex-1 max-w-md">
                <input
                  type="text"
                  value={subnetCidr}
                  onChange={(e) => setSubnetCidr(e.target.value)}
                  placeholder="e.g. 192.168.10.0/24 or 10.0.0.0/24"
                  className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-xs font-mono font-semibold text-surface-900 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white"
                />
              </div>

              {/* Mode Toggle */}
              <div className="flex rounded-lg border border-surface-200 bg-surface-100 p-0.5 text-xs font-semibold dark:border-white/10 dark:bg-surface-800">
                <button
                  type="button"
                  onClick={() => setScanMode('fast')}
                  className={`rounded-md px-2.5 py-1 transition ${
                    scanMode === 'fast'
                      ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-700 dark:text-white'
                      : 'text-surface-500 hover:text-surface-900 dark:text-surface-400'
                  }`}
                >
                  Fast (Top Ports)
                </button>
                <button
                  type="button"
                  onClick={() => setScanMode('deep')}
                  className={`rounded-md px-2.5 py-1 transition ${
                    scanMode === 'deep'
                      ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-700 dark:text-white'
                      : 'text-surface-500 hover:text-surface-900 dark:text-surface-400'
                  }`}
                >
                  Deep (Edge Probing)
                </button>
              </div>

              <button
                type="submit"
                disabled={scanning}
                className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 disabled:opacity-50 transition"
                data-testid="start-scan-btn"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${scanning ? 'animate-spin' : ''}`} />
                <span>{scanning ? t('inventory.scanning', 'Scanning Subnet...') : t('inventory.runScan', 'Scan Subnet')}</span>
              </button>
            </div>

            {/* Preset shortcuts */}
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-surface-500 dark:text-surface-400">
              <span className="text-[10px] uppercase font-semibold">Presets:</span>
              {['192.168.10.0/24', '10.0.0.0/24', '172.16.0.0/24'].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setSubnetCidr(preset)}
                  className="rounded border border-surface-200 bg-white px-1.5 py-0.5 hover:border-brand-500 dark:border-white/10 dark:bg-surface-800"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>
        </form>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-800 dark:border-red-900/40 dark:bg-red-950/40 dark:text-red-300">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
              <span>{error}</span>
            </div>
          )}

          {importSuccessMsg && (
            <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800 dark:border-emerald-900/40 dark:bg-emerald-950/40 dark:text-emerald-300">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
              <span>{importSuccessMsg}</span>
            </div>
          )}

          {discoveryResult ? (
            <div className="space-y-4">
              {/* Telemetry Strip */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-xl border border-surface-200 bg-white p-3 dark:border-white/10 dark:bg-surface-900">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                    Subnet Scope
                  </span>
                  <p className="mt-1 font-mono text-sm font-bold text-surface-900 dark:text-white">
                    {discoveryResult.subnet_cidr}
                  </p>
                </div>
                <div className="rounded-xl border border-surface-200 bg-white p-3 dark:border-white/10 dark:bg-surface-900">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                    Probed Addresses
                  </span>
                  <p className="mt-1 font-mono text-sm font-bold text-surface-900 dark:text-white">
                    {discoveryResult.total_probed} hosts
                  </p>
                </div>
                <div className="rounded-xl border border-surface-200 bg-white p-3 dark:border-white/10 dark:bg-surface-900">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                    Discovered Live
                  </span>
                  <p className="mt-1 font-mono text-sm font-bold text-emerald-600 dark:text-emerald-400">
                    {discoveryResult.discovered_count} active
                  </p>
                </div>
                <div className="rounded-xl border border-surface-200 bg-white p-3 dark:border-white/10 dark:bg-surface-900">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                    Scan Duration
                  </span>
                  <p className="mt-1 font-mono text-sm font-bold text-surface-900 dark:text-white">
                    {discoveryResult.scan_duration_ms} ms
                  </p>
                </div>
              </div>

              {/* Candidates Table */}
              <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs dark:border-white/10 dark:bg-surface-900">
                <div className="flex items-center justify-between border-b border-surface-200 px-4 py-2.5 dark:border-white/10 bg-surface-50/50 dark:bg-surface-950/40">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="select-all-candidates"
                      checked={unregisteredCount > 0 && selectedIps.size === unregisteredCount}
                      onChange={toggleSelectAll}
                      className="rounded border-surface-300 text-brand-600 focus:ring-brand-500 dark:border-white/20 dark:bg-surface-800"
                    />
                    <label
                      htmlFor="select-all-candidates"
                      className="text-xs font-semibold text-surface-700 dark:text-surface-300 cursor-pointer"
                    >
                      Select All New ({unregisteredCount})
                    </label>
                  </div>
                  <span className="text-[11px] font-mono text-surface-500 dark:text-surface-400">
                    {selectedIps.size} nodes selected
                  </span>
                </div>

                <div className="overflow-x-auto max-h-72">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600 dark:border-white/5 dark:bg-surface-800/60 dark:text-surface-300 sticky top-0">
                      <tr>
                        <th className="px-4 py-2 w-8"></th>
                        <th className="px-4 py-2">Host / IP Address</th>
                        <th className="px-4 py-2">MAC Address</th>
                        <th className="px-4 py-2">Device Type</th>
                        <th className="px-4 py-2">Open Ports</th>
                        <th className="px-4 py-2">Latency</th>
                        <th className="px-4 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-100 text-surface-700 dark:divide-white/5 dark:text-surface-300">
                      {discoveryResult.candidates.map((c) => (
                        <tr
                          key={c.ip_address}
                          className={`transition-colors ${
                            c.already_registered
                              ? 'opacity-60 bg-surface-50/30 dark:bg-surface-950/20'
                              : 'hover:bg-surface-50/80 dark:hover:bg-surface-800/40'
                          }`}
                        >
                          <td className="px-4 py-2.5">
                            <input
                              type="checkbox"
                              checked={selectedIps.has(c.ip_address)}
                              disabled={c.already_registered}
                              onChange={() => toggleIp(c.ip_address)}
                              className="rounded border-surface-300 text-brand-600 focus:ring-brand-500 dark:border-white/20 dark:bg-surface-800"
                            />
                          </td>
                          <td className="px-4 py-2.5">
                            <div className="flex flex-col">
                              <span className="font-semibold text-surface-900 dark:text-white">
                                {c.hostname}
                              </span>
                              <span className="font-mono text-[11px] text-surface-500 dark:text-surface-400">
                                {c.ip_address}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-2.5 font-mono text-[11px] text-surface-600 dark:text-surface-400">
                            {c.mac_address}
                          </td>
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-1.5 capitalize font-medium">
                              {getTypeIcon(c.detected_device_type)}
                              <span>{c.detected_device_type}</span>
                            </div>
                          </td>
                          <td className="px-4 py-2.5">
                            <div className="flex flex-wrap gap-1 max-w-[160px]">
                              {c.open_ports.map((p) => (
                                <span
                                  key={p}
                                  className="rounded bg-surface-100 px-1 py-0.2 font-mono text-[10px] font-semibold text-surface-700 dark:bg-surface-800 dark:text-surface-300"
                                >
                                  {p}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-2.5 font-mono text-[11px] text-surface-500 dark:text-surface-400">
                            {c.response_time_ms} ms
                          </td>
                          <td className="px-4 py-2.5">
                            {c.already_registered ? (
                              <Badge variant="mono" size="xs">
                                REGISTERED
                              </Badge>
                            ) : (
                              <Badge variant="online" size="xs" dot={true}>
                                NEW NODE
                              </Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-surface-200 dark:border-white/10 p-12 text-center">
              <Network className="mx-auto h-10 w-10 text-surface-400" />
              <p className="mt-3 text-xs font-semibold text-surface-700 dark:text-surface-300">
                Ready to probe subnet
              </p>
              <p className="mt-1 text-xs text-surface-400">
                Enter your network CIDR above and click "Scan Subnet" to discover unmanaged devices.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-surface-200 dark:border-white/10 px-6 py-4 bg-surface-50/50 dark:bg-surface-950/40">
          <span className="text-xs font-mono text-surface-500 dark:text-surface-400">
            {selectedIps.size} nodes ready for bulk import
          </span>
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-surface-200 bg-white px-3.5 py-2 text-xs font-semibold text-surface-700 hover:bg-surface-50 dark:border-white/10 dark:bg-surface-800 dark:text-surface-300"
            >
              {t('common.cancel', 'Cancel')}
            </button>
            <button
              type="button"
              disabled={importing || selectedIps.size === 0}
              onClick={handleImport}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-emerald-700 disabled:opacity-50 transition"
              data-testid="bulk-import-btn"
            >
              {importing ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Check className="h-3.5 w-3.5" />
              )}
              <span>
                {t('inventory.importSelected', 'Import {{count}} Hosts', {
                  count: selectedIps.size,
                })}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
