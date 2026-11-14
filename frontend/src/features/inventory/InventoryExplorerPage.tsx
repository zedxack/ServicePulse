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
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t('dashboard.online')}
          </span>
        );
      case 'offline':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-[11px] font-semibold text-rose-700 ring-1 ring-rose-200">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            {t('dashboard.offline')}
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700 ring-1 ring-amber-200">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {t('dashboard.warning')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2.5 py-0.5 text-[11px] font-semibold text-surface-700 ring-1 ring-surface-300">
            <span className="h-1.5 w-1.5 rounded-full bg-surface-400" />
            {t('dashboard.unknown')}
          </span>
        );
    }
  };

  const getDeviceIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'server':
        return <Server className="h-4 w-4 text-brand-600" />;
      case 'router':
      case 'switch':
        return <Wifi className="h-4 w-4 text-emerald-600" />;
      default:
        return <Monitor className="h-4 w-4 text-surface-600" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-surface-900">{t('inventory.title')}</h2>
          <p className="text-xs text-surface-500">{t('inventory.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              refetchTree();
              refetchDevices();
            }}
            className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-semibold text-surface-700 shadow-xs hover:bg-surface-50"
          >
            <RefreshCw className="h-3.5 w-3.5 text-surface-500" />
            <span>{t('dashboard.refresh')}</span>
          </button>
          {canEdit && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-brand-700"
            >
              <Plus className="h-4 w-4" />
              <span>{t('inventory.addDevice')}</span>
            </button>
          )}
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-2 text-surface-500">
            <Building2 className="h-4 w-4 text-brand-600" />
            <span className="text-xs font-medium">{t('inventory.totalBuildings')}</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-surface-900">
            {treeLoading ? '—' : treeData?.total_buildings ?? 0}
          </p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-2 text-surface-500">
            <Layers className="h-4 w-4 text-indigo-600" />
            <span className="text-xs font-medium">{t('inventory.totalFloors')}</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-surface-900">
            {treeLoading ? '—' : treeData?.total_floors ?? 0}
          </p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-2 text-surface-500">
            <DoorOpen className="h-4 w-4 text-amber-600" />
            <span className="text-xs font-medium">{t('inventory.totalRooms')}</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-surface-900">
            {treeLoading ? '—' : treeData?.total_rooms ?? 0}
          </p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <div className="flex items-center gap-2 text-surface-500">
            <HardDrive className="h-4 w-4 text-emerald-600" />
            <span className="text-xs font-medium">{t('inventory.totalDevices')}</span>
          </div>
          <p className="mt-2 text-2xl font-bold text-surface-900">
            {treeLoading ? '—' : treeData?.total_devices ?? 0}
          </p>
        </div>
      </div>

      {/* View Switcher & Filters */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 bg-white p-3 shadow-xs sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1 rounded-lg border border-surface-200 bg-surface-50 p-1 text-xs font-semibold">
          <button
            onClick={() => setViewMode('tree')}
            className={`rounded-md px-3 py-1 transition ${
              viewMode === 'tree' ? 'bg-white text-brand-700 shadow-xs' : 'text-surface-600 hover:text-surface-900'
            }`}
          >
            {t('inventory.treeView')}
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`rounded-md px-3 py-1 transition ${
              viewMode === 'list' ? 'bg-white text-brand-700 shadow-xs' : 'text-surface-600 hover:text-surface-900'
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
              className="w-full rounded-lg border border-surface-200 bg-surface-50 py-1.5 pl-8 pr-3 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:bg-white focus:outline-none"
            />
          </div>

          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="rounded-lg border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-xs font-medium text-surface-700 focus:outline-none"
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
            className="rounded-lg border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-xs font-medium text-surface-700 focus:outline-none"
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
        <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-xs">
          {treeLoading ? (
            <div className="space-y-4 py-8 text-center text-xs text-surface-500">
              <RefreshCw className="mx-auto h-6 w-6 animate-spin text-brand-500" />
              <span>{t('dashboard.loading')}</span>
            </div>
          ) : treeError ? (
            <div className="rounded-lg bg-rose-50 p-6 text-center text-xs font-semibold text-rose-700">
              <AlertCircle className="mx-auto h-6 w-6 text-rose-600 mb-2" />
              {t('dashboard.errorLoading')}
            </div>
          ) : !treeData?.buildings || treeData.buildings.length === 0 ? (
            <div className="py-12 text-center">
              <Building2 className="mx-auto h-10 w-10 text-surface-300" />
              <p className="mt-2 text-xs font-semibold text-surface-700">{t('inventory.noBuildings')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {treeData.buildings.map((building) => {
                const isBExpanded = !!expandedBuildings[building.id];
                return (
                  <div key={building.id} className="rounded-xl border border-surface-200 overflow-hidden">
                    {/* Building Item */}
                    <div
                      onClick={() => toggleBuilding(building.id)}
                      className="flex cursor-pointer items-center justify-between bg-surface-50/75 px-4 py-3 hover:bg-surface-100/75 transition"
                    >
                      <div className="flex items-center gap-3">
                        {isBExpanded ? (
                          <ChevronDown className="h-4 w-4 text-surface-500" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-surface-500" />
                        )}
                        <Building2 className="h-4 w-4 text-brand-600" />
                        <span className="font-bold text-xs text-surface-900">{building.name}</span>
                        <span className="rounded bg-surface-200 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-surface-700">
                          {building.code}
                        </span>
                        {building.address && (
                          <span className="hidden sm:inline text-[11px] text-surface-500">
                            &bull; {building.address}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] font-medium text-surface-500">
                        {building.floors.length} {t('inventory.totalFloors').toLowerCase()}
                      </span>
                    </div>

                    {/* Floors inside building */}
                    {isBExpanded && (
                      <div className="divide-y divide-surface-100 bg-white pl-6">
                        {building.floors.length === 0 ? (
                          <div className="p-3 text-[11px] text-surface-400">Qavatlar mavjud emas</div>
                        ) : (
                          building.floors.map((floor) => {
                            const isFExpanded = !!expandedFloors[floor.id];
                            return (
                              <div key={floor.id} className="py-2">
                                <div
                                  onClick={() => toggleFloor(floor.id)}
                                  className="flex cursor-pointer items-center justify-between py-1 px-3 rounded-lg hover:bg-surface-50"
                                >
                                  <div className="flex items-center gap-2">
                                    {isFExpanded ? (
                                      <ChevronDown className="h-3.5 w-3.5 text-surface-400" />
                                    ) : (
                                      <ChevronRight className="h-3.5 w-3.5 text-surface-400" />
                                    )}
                                    <Layers className="h-3.5 w-3.5 text-indigo-600" />
                                    <span className="text-xs font-semibold text-surface-800">
                                      Level {floor.level}: {floor.name}
                                    </span>
                                  </div>
                                  <span className="text-[11px] text-surface-500">
                                    {floor.rooms.length} {t('inventory.totalRooms').toLowerCase()}
                                  </span>
                                </div>

                                {/* Rooms inside floor */}
                                {isFExpanded && (
                                  <div className="pl-6 pt-2 space-y-2">
                                    {floor.rooms.length === 0 ? (
                                      <div className="text-[11px] text-surface-400 py-1">Xonalar mavjud emas</div>
                                    ) : (
                                      floor.rooms.map((room) => (
                                        <div key={room.id} className="rounded-lg border border-surface-150 bg-surface-50/40 p-3">
                                          <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                              <DoorOpen className="h-3.5 w-3.5 text-amber-600" />
                                              <span className="text-xs font-semibold text-surface-900">
                                                {room.room_number} &bull; {room.name}
                                              </span>
                                            </div>
                                            <span className="text-[10px] text-surface-500 font-medium">
                                              {room.devices.length} {t('inventory.totalDevices').toLowerCase()}
                                            </span>
                                          </div>

                                          {/* Devices inside room */}
                                          {room.devices.length === 0 ? (
                                            <div className="text-[11px] text-surface-400">{t('inventory.noDevices')}</div>
                                          ) : (
                                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                                              {room.devices.map((device) => (
                                                <div
                                                  key={device.id}
                                                  onClick={() => setSelectedDevice(device)}
                                                  className="flex cursor-pointer items-center justify-between rounded-lg border border-surface-200 bg-white p-2.5 shadow-2xs hover:border-brand-300 hover:shadow-xs transition"
                                                >
                                                  <div className="flex items-center gap-2">
                                                    {getDeviceIcon(device.device_type)}
                                                    <div className="min-w-0">
                                                      <p className="truncate text-xs font-bold text-surface-900">
                                                        {device.name}
                                                      </p>
                                                      <p className="font-mono text-[10px] text-surface-500">
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
        <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs">
          {devicesLoading ? (
            <div className="py-12 text-center text-xs text-surface-500">{t('dashboard.loading')}</div>
          ) : devicesError ? (
            <div className="p-6 text-center text-xs text-rose-600">{t('dashboard.errorLoading')}</div>
          ) : filteredDevices.length === 0 ? (
            <div className="py-12 text-center text-xs text-surface-500">{t('inventory.noDevices')}</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-surface-700">
                <thead className="border-b border-surface-200 bg-surface-50/75 text-[11px] font-semibold uppercase tracking-wider text-surface-500">
                  <tr>
                    <th className="py-3 px-4">{t('common.title')}</th>
                    <th className="py-3 px-4">Hostname</th>
                    <th className="py-3 px-4">{t('inventory.ipAddress')}</th>
                    <th className="py-3 px-4">{t('inventory.type')}</th>
                    <th className="py-3 px-4">{t('inventory.os')}</th>
                    <th className="py-3 px-4">{t('common.status')}</th>
                    <th className="py-3 px-4 text-right">{t('common.action')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {filteredDevices.map((device) => (
                    <tr key={device.id} className="hover:bg-surface-50/50 transition">
                      <td className="py-3 px-4 font-bold text-surface-900">
                        <div className="flex items-center gap-2">
                          {getDeviceIcon(device.device_type)}
                          <span>{device.name}</span>
                          {device.is_sample_data && (
                            <span className="rounded bg-surface-100 px-1 text-[9px] font-semibold text-surface-600">
                              Demo
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-surface-600">{device.hostname}</td>
                      <td className="py-3 px-4 font-mono text-surface-900">{device.ip_address}</td>
                      <td className="py-3 px-4 capitalize">{device.device_type}</td>
                      <td className="py-3 px-4">{device.operating_system || '—'}</td>
                      <td className="py-3 px-4">{getStatusBadge(device.status)}</td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => setSelectedDevice(device)}
                          className="rounded-md bg-surface-100 px-2.5 py-1 text-[11px] font-semibold text-brand-700 hover:bg-brand-50"
                        >
                          {t('incidents.details')}
                        </button>
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
