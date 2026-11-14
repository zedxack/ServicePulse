import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  Building2,
  ChevronDown,
  ChevronRight,
  DoorOpen,
  HardDrive,
  Layers,
  Monitor,
  Plus,
  RefreshCw,
  Search,
  Server,
  Wifi,
} from 'lucide-react';
import { inventoryApi } from '../../shared/api/inventory';
import { DeviceRead } from '../../shared/types/inventory';
import { DeviceDetailModal } from './DeviceDetailModal';
import { CreateLocationModal } from './CreateLocationModal';
import { useAuth } from '../auth/AuthContext';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { EmptyState } from '../../shared/components/EmptyState';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';

export const InventoryExplorerPage: React.FC = () => {
  const { t } = useTranslation();
  const { hasAnyRole } = useAuth();
  const [viewMode, setViewMode] = useState<'tree' | 'list'>('tree');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedDevice, setSelectedDevice] = useState<DeviceRead | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [expandedBuildings, setExpandedBuildings] = useState<Record<number, boolean>>({});
  const [expandedFloors, setExpandedFloors] = useState<Record<number, boolean>>({});

  const canEdit = hasAnyRole(['platform_super_admin', 'company_admin', 'it_admin', 'admin', 'support']);

  const {
    data: treeData,
    isLoading: treeLoading,
    error: treeError,
    refetch: refetchTree,
  } = useQuery({
    queryKey: ['inventoryTree'],
    queryFn: inventoryApi.getInventoryTree,
  });

  const {
    data: devicesData,
    isLoading: devicesLoading,
    error: devicesError,
    refetch: refetchDevices,
  } = useQuery({
    queryKey: ['devicesList', selectedType, selectedStatus],
    queryFn: () =>
      inventoryApi.listDevices({
        device_type: selectedType !== 'all' ? selectedType : undefined,
        device_status: selectedStatus !== 'all' ? selectedStatus : undefined,
        limit: 100,
      }),
  });

  const toggleBuilding = (id: number) => {
    setExpandedBuildings((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleFloor = (id: number) => {
    setExpandedFloors((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredDevices = (devicesData || []).filter((d) => {
    const q = searchQuery.toLowerCase();
    return (
      d.name.toLowerCase().includes(q) ||
      d.hostname.toLowerCase().includes(q) ||
      d.ip_address.toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online':
        return <Badge variant="online" size="sm">{t('dashboard.online')}</Badge>;
      case 'offline':
        return <Badge variant="offline" size="sm">{t('dashboard.offline')}</Badge>;
      case 'warning':
        return <Badge variant="warning" size="sm">{t('dashboard.warning')}</Badge>;
      default:
        return <Badge variant="mono" size="sm">{t('dashboard.unknown')}</Badge>;
    }
  };

  const getDeviceIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'server':
        return <Server className="h-4 w-4 text-brand-600 dark:text-brand-400" />;
      case 'router':
      case 'switch':
        return <Wifi className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />;
      default:
        return <Monitor className="h-4 w-4 text-surface-500 dark:text-surface-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('inventory.title')}
            </h1>
            <span className="rounded-md border border-brand-500/20 bg-brand-500/10 px-2 py-0.5 text-[11px] font-semibold text-brand-600 dark:text-brand-400">
              CMDB Explorer
            </span>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400">{t('inventory.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              refetchTree();
              refetchDevices();
            }}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            {t('dashboard.refresh')}
          </Button>
          {canEdit && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsCreateModalOpen(true)}
              leftIcon={<Plus className="h-3.5 w-3.5" />}
            >
              {t('inventory.addDevice')}
            </Button>
          )}
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          title={t('inventory.totalBuildings')}
          value={treeLoading ? '—' : treeData?.total_buildings ?? 0}
          subtitle="Campuses & facilities"
          icon={<Building2 className="h-4 w-4" />}
          accentColor="brand"
        />
        <MetricCard
          title={t('inventory.totalFloors')}
          value={treeLoading ? '—' : treeData?.total_floors ?? 0}
          subtitle="Physical operational tiers"
          icon={<Layers className="h-4 w-4" />}
          accentColor="purple"
        />
        <MetricCard
          title={t('inventory.totalRooms')}
          value={treeLoading ? '—' : treeData?.total_rooms ?? 0}
          subtitle="Server rooms & offices"
          icon={<DoorOpen className="h-4 w-4" />}
          accentColor="amber"
        />
        <MetricCard
          title={t('inventory.totalDevices')}
          value={treeLoading ? '—' : treeData?.total_devices ?? 0}
          subtitle="Monitored endpoint inventory"
          icon={<HardDrive className="h-4 w-4" />}
          accentColor="emerald"
        />
      </div>

      {/* View Switcher & Filters */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-3 shadow-xs transition-colors sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1 rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/60 p-1 text-xs font-semibold">
          <button
            onClick={() => setViewMode('tree')}
            className={`rounded-md px-3 py-1 transition ${
              viewMode === 'tree'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white'
            }`}
          >
            {t('inventory.treeView')}
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`rounded-md px-3 py-1 transition ${
              viewMode === 'list'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white'
            }`}
          >
            {t('inventory.listView')}
          </button>
        </div>

        <div className="flex flex-1 flex-wrap items-center gap-2 sm:justify-end">
          <div className="relative min-w-[200px] flex-1 sm:max-w-xs">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-surface-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('inventory.searchDevices')}
              className="w-full rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 py-1.5 pl-8 pr-3 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:bg-white dark:focus:bg-surface-900 focus:outline-none transition-colors"
            />
          </div>

          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 px-2.5 py-1.5 text-xs font-medium text-surface-700 dark:text-surface-300 focus:outline-none"
          >
            <option value="all">{t('inventory.allTypes')}</option>
            <option value="server">Server</option>
            <option value="workstation">Workstation</option>
            <option value="router">Router</option>
            <option value="switch">Switch</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 px-2.5 py-1.5 text-xs font-medium text-surface-700 dark:text-surface-300 focus:outline-none"
          >
            <option value="all">{t('inventory.allStatuses')}</option>
            <option value="online">{t('dashboard.online')}</option>
            <option value="offline">{t('dashboard.offline')}</option>
            <option value="warning">{t('dashboard.warning')}</option>
          </select>
        </div>
      </div>

      {/* Main Content Area */}
      {viewMode === 'tree' ? (
        <div className="rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-6 shadow-xs transition-colors">
          {treeLoading ? (
            <div className="space-y-4">
              <LoadingSkeleton height="h-16" />
              <LoadingSkeleton height="h-16" />
              <LoadingSkeleton height="h-16" />
            </div>
          ) : treeError ? (
            <div className="rounded-lg bg-rose-50 dark:bg-rose-950/20 p-6 text-center text-xs font-semibold text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900/50">
              <AlertCircle className="mx-auto h-6 w-6 text-rose-600 mb-2" />
              {t('dashboard.errorLoading')}
            </div>
          ) : !treeData?.buildings || treeData.buildings.length === 0 ? (
            <div className="py-12">
              <EmptyState
                icon={<Building2 className="h-8 w-8" />}
                title={t('inventory.noBuildings')}
                description="No campus structures configured. Click 'Add Asset / Location' to create your first facility."
                action={
                  canEdit ? (
                    <Button size="sm" onClick={() => setIsCreateModalOpen(true)}>
                      {t('inventory.addDevice')}
                    </Button>
                  ) : undefined
                }
              />
            </div>
          ) : (
            <div className="space-y-3">
              {treeData.buildings.map((building) => {
                const isBExpanded = !!expandedBuildings[building.id];
                return (
                  <div
                    key={building.id}
                    className="rounded-xl border border-surface-200 dark:border-surface-800 overflow-hidden bg-white dark:bg-surface-900 transition-colors"
                  >
                    {/* Building Item */}
                    <div
                      onClick={() => toggleBuilding(building.id)}
                      className="flex cursor-pointer items-center justify-between bg-surface-50/75 dark:bg-surface-800/50 px-4 py-3 hover:bg-surface-100/75 dark:hover:bg-surface-800 transition"
                    >
                      <div className="flex items-center gap-3">
                        {isBExpanded ? (
                          <ChevronDown className="h-4 w-4 text-surface-400" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-surface-400" />
                        )}
                        <Building2 className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                        <span className="font-bold text-xs text-surface-900 dark:text-white">
                          {building.name}
                        </span>
                        <span className="rounded bg-surface-200 dark:bg-surface-700 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-surface-700 dark:text-surface-300">
                          {building.code}
                        </span>
                        {building.address && (
                          <span className="hidden sm:inline text-[11px] text-surface-500 dark:text-surface-400">
                            &bull; {building.address}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
                        {building.floors.length} {t('inventory.totalFloors').toLowerCase()}
                      </span>
                    </div>

                    {/* Floors inside building */}
                    {isBExpanded && (
                      <div className="divide-y divide-surface-100 dark:divide-surface-800 bg-white dark:bg-surface-900 pl-6">
                        {building.floors.length === 0 ? (
                          <div className="p-3 text-[11px] text-surface-400">No floors added to this building</div>
                        ) : (
                          building.floors.map((floor) => {
                            const isFExpanded = !!expandedFloors[floor.id];
                            return (
                              <div key={floor.id} className="py-2">
                                <div
                                  onClick={() => toggleFloor(floor.id)}
                                  className="flex cursor-pointer items-center justify-between py-1 px-3 rounded-lg hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors"
                                >
                                  <div className="flex items-center gap-2">
                                    {isFExpanded ? (
                                      <ChevronDown className="h-3.5 w-3.5 text-surface-400" />
                                    ) : (
                                      <ChevronRight className="h-3.5 w-3.5 text-surface-400" />
                                    )}
                                    <Layers className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                                    <span className="text-xs font-semibold text-surface-800 dark:text-surface-200">
                                      Level {floor.level}: {floor.name}
                                    </span>
                                  </div>
                                  <span className="text-[11px] text-surface-500 dark:text-surface-400">
                                    {floor.rooms.length} {t('inventory.totalRooms').toLowerCase()}
                                  </span>
                                </div>

                                {/* Rooms inside floor */}
                                {isFExpanded && (
                                  <div className="pl-6 pt-2 space-y-2">
                                    {floor.rooms.length === 0 ? (
                                      <div className="text-[11px] text-surface-400 py-1">No rooms added to this floor</div>
                                    ) : (
                                      floor.rooms.map((room) => (
                                        <div
                                          key={room.id}
                                          className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50/50 dark:bg-surface-950/40 p-3"
                                        >
                                          <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                              <DoorOpen className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                                              <span className="text-xs font-semibold text-surface-900 dark:text-white">
                                                {room.room_number} &bull; {room.name}
                                              </span>
                                            </div>
                                            <span className="text-[10px] text-surface-500 font-medium">
                                              {room.devices.length} {t('inventory.totalDevices').toLowerCase()}
                                            </span>
                                          </div>

                                          {/* Devices inside room */}
                                          {room.devices.length === 0 ? (
                                            <div className="text-[11px] text-surface-400">
                                              {t('inventory.noDevices')}
                                            </div>
                                          ) : (
                                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                                              {room.devices.map((device) => (
                                                <div
                                                  key={device.id}
                                                  onClick={() => setSelectedDevice(device)}
                                                  className="flex cursor-pointer items-center justify-between rounded-lg border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-2.5 shadow-2xs hover:border-brand-400 dark:hover:border-brand-500 hover:shadow-xs transition"
                                                >
                                                  <div className="flex items-center gap-2">
                                                    {getDeviceIcon(device.device_type)}
                                                    <div className="min-w-0">
                                                      <p className="truncate text-xs font-bold text-surface-900 dark:text-white">
                                                        {device.name}
                                                      </p>
                                                      <p className="font-mono text-[10px] text-surface-500 dark:text-surface-400">
                                                        {device.ip_address}
                                                      </p>
                                                    </div>
                                                  </div>
                                                  {getStatusBadge(device.status)}
                                                </div>
                                              ))}
                                            </div>
                                          )}
                                        </div>
                                      ))
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        /* List View */
        <div className="overflow-hidden rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-xs transition-colors">
          {devicesLoading ? (
            <div className="p-6 space-y-3">
              <LoadingSkeleton height="h-10" />
              <LoadingSkeleton height="h-10" />
              <LoadingSkeleton height="h-10" />
            </div>
          ) : devicesError ? (
            <div className="p-6 text-center text-xs text-rose-600 dark:text-rose-400">
              {t('dashboard.errorLoading')}
            </div>
          ) : filteredDevices.length === 0 ? (
            <div className="py-12">
              <EmptyState
                icon={<HardDrive className="h-8 w-8" />}
                title={t('inventory.noDevices')}
                description="No matching assets found matching your search or filters."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-surface-700 dark:text-surface-300">
                <thead className="border-b border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                  <tr>
                    <th className="py-3.5 px-4">{t('common.title')}</th>
                    <th className="py-3.5 px-4">Hostname</th>
                    <th className="py-3.5 px-4">{t('inventory.ipAddress')}</th>
                    <th className="py-3.5 px-4">{t('inventory.type')}</th>
                    <th className="py-3.5 px-4">{t('inventory.os')}</th>
                    <th className="py-3.5 px-4">{t('common.status')}</th>
                    <th className="py-3.5 px-4 text-right">{t('common.action')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 dark:divide-surface-800/80">
                  {filteredDevices.map((device) => (
                    <tr
                      key={device.id}
                      className="hover:bg-surface-50/70 dark:hover:bg-surface-800/40 transition-colors"
                    >
                      <td className="py-3.5 px-4 font-bold text-surface-900 dark:text-white">
                        <div className="flex items-center gap-2">
                          {getDeviceIcon(device.device_type)}
                          <span>{device.name}</span>
                          {device.is_sample_data && (
                            <span className="rounded bg-surface-100 dark:bg-surface-800 px-1 text-[9px] font-semibold text-surface-600 dark:text-surface-400">
                              Demo
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-surface-600 dark:text-surface-400">
                        {device.hostname}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-surface-900 dark:text-white font-semibold">
                        {device.ip_address}
                      </td>
                      <td className="py-3.5 px-4 capitalize text-surface-600 dark:text-surface-300">
                        {device.device_type}
                      </td>
                      <td className="py-3.5 px-4 text-surface-600 dark:text-surface-400">
                        {device.operating_system || '—'}
                      </td>
                      <td className="py-3.5 px-4">{getStatusBadge(device.status)}</td>
                      <td className="py-3.5 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedDevice(device)}
                        >
                          {t('incidents.details')}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {selectedDevice && (
        <DeviceDetailModal device={selectedDevice} onClose={() => setSelectedDevice(null)} />
      )}

      {isCreateModalOpen && treeData?.buildings && (
        <CreateLocationModal
          buildings={treeData.buildings}
          onClose={() => setIsCreateModalOpen(false)}
        />
      )}
    </div>
  );
};
