export interface DeviceRead {
  id: number;
  name: string;
  hostname: string;
  ip_address: string;
  mac_address?: string | null;
  device_type: 'server' | 'workstation' | 'router' | 'switch' | 'printer' | string;
  operating_system?: string | null;
  organization_id?: number | null;
  is_monitored: boolean;
  is_sample_data: boolean;
  room_id?: number | null;
  status: 'online' | 'offline' | 'warning' | 'unknown' | string;
  last_seen?: string | null;
  last_heartbeat?: string | null;
  consecutive_failures: number;
  created_at: string;
}

export interface DeviceCreate {
  name: string;
  hostname: string;
  ip_address: string;
  mac_address?: string | null;
  device_type?: string;
  operating_system?: string | null;
  organization_id?: number | null;
  is_monitored?: boolean;
  is_sample_data?: boolean;
  room_id?: number | null;
}

export interface DeviceUpdate {
  name?: string;
  hostname?: string;
  ip_address?: string;
  mac_address?: string | null;
  device_type?: string;
  operating_system?: string | null;
  status?: string;
  is_monitored?: boolean;
  room_id?: number | null;
}

export interface RoomRead {
  id: number;
  floor_id: number;
  room_number: string;
  name: string;
  description?: string | null;
  is_sample_data: boolean;
  devices: DeviceRead[];
  created_at: string;
}

export interface RoomCreate {
  floor_id: number;
  room_number: string;
  name: string;
  description?: string | null;
  is_sample_data?: boolean;
}

export interface FloorRead {
  id: number;
  building_id: number;
  level: number;
  name: string;
  description?: string | null;
  is_sample_data: boolean;
  rooms: RoomRead[];
  created_at: string;
}

export interface FloorCreate {
  building_id: number;
  level: number;
  name: string;
  description?: string | null;
  is_sample_data?: boolean;
}

export interface BuildingRead {
  id: number;
  organization_id?: number | null;
  name: string;
  code: string;
  address?: string | null;
  description?: string | null;
  is_sample_data: boolean;
  floors: FloorRead[];
  created_at: string;
}

export interface BuildingCreate {
  name: string;
  code: string;
  address?: string | null;
  description?: string | null;
  organization_id?: number | null;
  is_sample_data?: boolean;
}

export interface InventoryTreeResponse {
  total_buildings: number;
  total_floors: number;
  total_rooms: number;
  total_devices: number;
  buildings: BuildingRead[];
}

export interface NetworkCheckRead {
  id: number;
  device_id: number;
  check_type: 'icmp' | 'tcp' | 'http' | string;
  target: string;
  port?: number | null;
  is_success: boolean;
  response_time_ms?: number | null;
  error_message?: string | null;
  checked_at: string;
}

export interface AgentTelemetryRead {
  id: number;
  agent_id: number;
  cpu_percent: number;
  ram_percent: number;
  ram_used_mb: number;
  ram_total_mb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  windows_activation_status?: string | null;
  windows_defender_status?: string | null;
  recorded_at: string;
  created_at: string;
}

export interface AgentRead {
  id: number;
  organization_id?: number | null;
  device_id?: number | null;
  agent_uuid: string;
  status: string;
  version: string;
  hostname: string;
  ip_address: string;
  os_name?: string | null;
  last_seen?: string | null;
  created_at: string;
}
