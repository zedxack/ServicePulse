import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, X } from 'lucide-react';
import { inventoryApi } from '../../shared/api/inventory';
import { BuildingRead } from '../../shared/types/inventory';
import { Button } from '../../shared/components/Button';

interface CreateLocationModalProps {
  buildings: BuildingRead[];
  onClose: () => void;
}

export const CreateLocationModal: React.FC<CreateLocationModalProps> = ({ buildings, onClose }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [activeForm, setActiveForm] = useState<'building' | 'floor' | 'room' | 'device'>('building');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Building form
  const [bName, setBName] = useState('');
  const [bCode, setBCode] = useState('');
  const [bAddress, setBAddress] = useState('');

  // Floor form
  const [selectedBId, setSelectedBId] = useState<number>(buildings[0]?.id || 0);
  const [fLevel, setFLevel] = useState<number>(1);
  const [fName, setFName] = useState('');

  // Room form
  const floorsForSelectedB = buildings.find((b) => b.id === selectedBId)?.floors || [];
  const [selectedFId, setSelectedFId] = useState<number>(floorsForSelectedB[0]?.id || 0);
  const [rNumber, setRNumber] = useState('');
  const [rName, setRName] = useState('');

  // Device form
  const roomsForSelectedF = floorsForSelectedB.find((f) => f.id === selectedFId)?.rooms || [];
  const [selectedRId, setSelectedRId] = useState<number>(roomsForSelectedF[0]?.id || 0);
  const [dName, setDName] = useState('');
  const [dHostname, setDHostname] = useState('');
  const [dIp, setDIp] = useState('');
  const [dType, setDType] = useState('workstation');
  const [dOs, setDOs] = useState('Windows 11 Pro');

  const createBuildingMutation = useMutation({
    mutationFn: inventoryApi.createBuilding,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventoryTree'] });
      queryClient.invalidateQueries({ queryKey: ['devicesList'] });
      onClose();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMsg(msg || 'Failed to create building');
    },
  });

  const createFloorMutation = useMutation({
    mutationFn: inventoryApi.createFloor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventoryTree'] });
      onClose();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMsg(msg || 'Failed to create floor');
    },
  });

  const createRoomMutation = useMutation({
    mutationFn: inventoryApi.createRoom,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventoryTree'] });
      onClose();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMsg(msg || 'Failed to create room');
    },
  });

  const createDeviceMutation = useMutation({
    mutationFn: inventoryApi.createDevice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventoryTree'] });
      queryClient.invalidateQueries({ queryKey: ['devicesList'] });
      onClose();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErrorMsg(msg || 'Failed to create device');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (activeForm === 'building') {
      createBuildingMutation.mutate({
        name: bName,
        code: bCode,
        address: bAddress || undefined,
      });
    } else if (activeForm === 'floor') {
      if (!selectedBId) {
        setErrorMsg('Please select a building');
        return;
      }
      createFloorMutation.mutate({
        building_id: selectedBId,
        level: fLevel,
        name: fName,
      });
    } else if (activeForm === 'room') {
      if (!selectedFId) {
        setErrorMsg('Please select a floor');
        return;
      }
      createRoomMutation.mutate({
        floor_id: selectedFId,
        room_number: rNumber,
        name: rName,
      });
    } else if (activeForm === 'device') {
      createDeviceMutation.mutate({
        name: dName,
        hostname: dHostname,
        ip_address: dIp,
        device_type: dType,
        operating_system: dOs,
        room_id: selectedRId || undefined,
      });
    }
  };

  const isPending =
    createBuildingMutation.isPending ||
    createFloorMutation.isPending ||
    createRoomMutation.isPending ||
    createDeviceMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div className="relative flex max-h-[90vh] w-full max-w-lg flex-col rounded-2xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-2xl transition-colors">
        <div className="flex items-center justify-between border-b border-surface-200 dark:border-surface-800 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500/10 text-brand-600 dark:text-brand-400">
              <Plus className="h-4 w-4" />
            </div>
            <h3 className="text-base font-bold text-surface-900 dark:text-white">
              Add Infrastructure Node
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

        {/* Form Selector Tabs */}
        <div className="grid grid-cols-4 border-b border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/60 p-1 text-center text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveForm('building')}
            className={`rounded-lg py-1.5 transition ${
              activeForm === 'building'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400'
            }`}
          >
            {t('inventory.totalBuildings')}
          </button>
          <button
            type="button"
            onClick={() => setActiveForm('floor')}
            className={`rounded-lg py-1.5 transition ${
              activeForm === 'floor'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400'
            }`}
          >
            {t('inventory.totalFloors')}
          </button>
          <button
            type="button"
            onClick={() => setActiveForm('room')}
            className={`rounded-lg py-1.5 transition ${
              activeForm === 'room'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400'
            }`}
          >
            {t('inventory.totalRooms')}
          </button>
          <button
            type="button"
            onClick={() => setActiveForm('device')}
            className={`rounded-lg py-1.5 transition ${
              activeForm === 'device'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400'
            }`}
          >
            {t('inventory.totalDevices')}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
          {errorMsg && (
            <div className="rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-3 text-xs font-medium text-rose-700 dark:text-rose-300">
              {errorMsg}
            </div>
          )}

          {activeForm === 'building' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('inventory.buildingName')}
                </label>
                <input
                  type="text"
                  required
                  value={bName}
                  onChange={(e) => setBName(e.target.value)}
                  placeholder="e.g. Headquarters Campus"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('inventory.buildingCode')}
                </label>
                <input
                  type="text"
                  required
                  value={bCode}
                  onChange={(e) => setBCode(e.target.value)}
                  placeholder="e.g. HQ-01"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('inventory.address')}
                </label>
                <input
                  type="text"
                  value={bAddress}
                  onChange={(e) => setBAddress(e.target.value)}
                  placeholder="e.g. 100 Main St"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
            </>
          )}

          {activeForm === 'floor' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('inventory.totalBuildings')}
                </label>
                <select
                  value={selectedBId}
                  onChange={(e) => setSelectedBId(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
                >
                  {buildings.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('inventory.level')}
                </label>
                <input
                  type="number"
                  required
                  value={fLevel}
                  onChange={(e) => setFLevel(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  Floor Name
                </label>
                <input
                  type="text"
                  required
                  value={fName}
                  onChange={(e) => setFName(e.target.value)}
                  placeholder="e.g. 2nd Floor Engineering Lab"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
            </>
          )}

          {activeForm === 'room' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('inventory.totalBuildings')}
                </label>
                <select
                  value={selectedBId}
                  onChange={(e) => {
                    const bId = Number(e.target.value);
                    setSelectedBId(bId);
                    const fList = buildings.find((b) => b.id === bId)?.floors || [];
                    setSelectedFId(fList[0]?.id || 0);
                  }}
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
                >
                  {buildings.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('inventory.totalFloors')}
                </label>
                <select
                  value={selectedFId}
                  onChange={(e) => setSelectedFId(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
                >
                  {floorsForSelectedB.map((f) => (
                    <option key={f.id} value={f.id}>
                      Level {f.level}: {f.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('inventory.roomNumber')}
                </label>
                <input
                  type="text"
                  required
                  value={rNumber}
                  onChange={(e) => setRNumber(e.target.value)}
                  placeholder="204"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  Room Name
                </label>
                <input
                  type="text"
                  required
                  value={rName}
                  onChange={(e) => setRName(e.target.value)}
                  placeholder="e.g. Server Room B"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
            </>
          )}

          {activeForm === 'device' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  Device Name
                </label>
                <input
                  type="text"
                  required
                  value={dName}
                  onChange={(e) => setDName(e.target.value)}
                  placeholder="Core Switch 01"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  Hostname
                </label>
                <input
                  type="text"
                  required
                  value={dHostname}
                  onChange={(e) => setDHostname(e.target.value)}
                  placeholder="sw-core-01.corp.internal"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('inventory.ipAddress')}
                </label>
                <input
                  type="text"
                  required
                  value={dIp}
                  onChange={(e) => setDIp(e.target.value)}
                  placeholder="192.168.10.1"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                    {t('inventory.type')}
                  </label>
                  <select
                    value={dType}
                    onChange={(e) => setDType(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
                  >
                    <option value="workstation">Workstation</option>
                    <option value="server">Server</option>
                    <option value="router">Router</option>
                    <option value="switch">Switch</option>
                    <option value="printer">Printer</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                    {t('inventory.os')}
                  </label>
                  <input
                    type="text"
                    value={dOs}
                    onChange={(e) => setDOs(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white focus:border-brand-500 focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  Room ID (Optional)
                </label>
                <input
                  type="number"
                  value={selectedRId || ''}
                  onChange={(e) => setSelectedRId(Number(e.target.value))}
                  placeholder="Room ID number"
                  className="mt-1 w-full rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-3 py-2 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
                />
              </div>
            </>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="secondary" size="sm" onClick={onClose}>
              {t('incidents.cancel')}
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isPending}>
              {isPending ? 'Saving...' : t('incidents.confirmAction')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
