import { apiClient } from './client';
import {
  AgentBootstrapConfigResponse,
  AgentRead,
  AgentTelemetryRead,
  BuildingCreate,
  BuildingRead,
  DeviceCreate,
  DeviceProcessSnapshotResponse,
  DeviceRead,
  DeviceUpdate,
  DiscoveredBulkImportRequest,
  DiscoveredBulkImportResponse,
  FloorCreate,
  FloorRead,
  InventoryTreeResponse,
  NetworkCheckRead,
  RemoteActionRequest,
  RemoteActionResponse,
  RoomCreate,
  RoomRead,
  SubnetDiscoveryRequest,
  SubnetDiscoveryResponse,
} from '../types/inventory';

export const inventoryApi = {
  getInventoryTree: async (): Promise<InventoryTreeResponse> => {
    const response = await apiClient.get<InventoryTreeResponse>('/inventory/tree');
    return response.data;
  },

  listDevices: async (params?: {
    skip?: number;
    limit?: number;
    device_type?: string;
    device_status?: string;
    room_id?: number;
  }): Promise<DeviceRead[]> => {
    const response = await apiClient.get<DeviceRead[]>('/inventory/devices', { params });
    return response.data;
  },

  getDevice: async (deviceId: number): Promise<DeviceRead> => {
    const response = await apiClient.get<DeviceRead>(`/inventory/devices/${deviceId}`);
    return response.data;
  },

  getDeviceNetworkChecks: async (
    deviceId: number,
    params?: { skip?: number; limit?: number }
  ): Promise<NetworkCheckRead[]> => {
    const response = await apiClient.get<NetworkCheckRead[]>(
      `/inventory/devices/${deviceId}/network-checks`,
      { params }
    );
    return response.data;
  },

  createBuilding: async (data: BuildingCreate): Promise<BuildingRead> => {
    const response = await apiClient.post<BuildingRead>('/inventory/buildings', data);
    return response.data;
  },

  createFloor: async (data: FloorCreate): Promise<FloorRead> => {
    const response = await apiClient.post<FloorRead>('/inventory/floors', data);
    return response.data;
  },

  createRoom: async (data: RoomCreate): Promise<RoomRead> => {
    const response = await apiClient.post<RoomRead>('/inventory/rooms', data);
    return response.data;
  },

  createDevice: async (data: DeviceCreate): Promise<DeviceRead> => {
    const response = await apiClient.post<DeviceRead>('/inventory/devices', data);
    return response.data;
  },

  updateDevice: async (deviceId: number, data: DeviceUpdate): Promise<DeviceRead> => {
    const response = await apiClient.patch<DeviceRead>(`/inventory/devices/${deviceId}`, data);
    return response.data;
  },

  deleteDevice: async (deviceId: number): Promise<void> => {
    await apiClient.delete(`/inventory/devices/${deviceId}`);
  },

  listAgents: async (): Promise<AgentRead[]> => {
    const response = await apiClient.get<AgentRead[]>('/agent');
    return response.data;
  },

  getAgentTelemetry: async (
    agentId: number,
    params?: { skip?: number; limit?: number }
  ): Promise<AgentTelemetryRead[]> => {
    const response = await apiClient.get<AgentTelemetryRead[]>(`/agent/${agentId}/telemetry`, {
      params,
    });
    return response.data;
  },

  discoverSubnet: async (req: SubnetDiscoveryRequest): Promise<SubnetDiscoveryResponse> => {
    const response = await apiClient.post<SubnetDiscoveryResponse>('/inventory/discover-subnet', req);
    return response.data;
  },

  importDiscovered: async (req: DiscoveredBulkImportRequest): Promise<DiscoveredBulkImportResponse> => {
    const response = await apiClient.post<DiscoveredBulkImportResponse>('/inventory/import-discovered', req);
    return response.data;
  },

  executeRemoteAction: async (
    deviceId: number,
    req: RemoteActionRequest
  ): Promise<RemoteActionResponse> => {
    const response = await apiClient.post<RemoteActionResponse>(
      `/inventory/devices/${deviceId}/remote-action`,
      req
    );
    return response.data;
  },

  getDeviceProcessSnapshot: async (deviceId: number): Promise<DeviceProcessSnapshotResponse> => {
    const response = await apiClient.get<DeviceProcessSnapshotResponse>(
      `/inventory/devices/${deviceId}/process-snapshot`
    );
    return response.data;
  },

  getAgentBootstrapConfig: async (): Promise<AgentBootstrapConfigResponse> => {
    const response = await apiClient.get<AgentBootstrapConfigResponse>('/agents/bootstrap-config');
    return response.data;
  },
};
