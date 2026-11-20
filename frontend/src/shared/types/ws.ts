/**
 * ServicePulse - WebSocket Real-Time Event Types
 * Author: Muhammadyusuf Usmonov
 *  */

export interface WSTicketResponse {
  ticket: string;
  expires_in_seconds: number;
}

export type WSEventType =
  | 'device:status_change'
  | 'device:telemetry'
  | 'incident:created'
  | 'incident:acknowledged'
  | 'incident:assigned'
  | 'incident:resolved'
  | 'remediation:status'
  | 'alert:created'
  | 'pong';

export interface DeviceStatusChangePayload {
  device_id: number;
  device_name: string;
  old_status: string;
  new_status: string;
}

export interface DeviceTelemetryPayload {
  agent_id: number;
  device_id: number | null;
  hostname: string;
  cpu_percent: number | null;
  ram_percent: number | null;
  disk_percent: number | null;
  windows_activation_status: string | null;
  windows_defender_status: string | null;
  recorded_at: string;
}

export interface IncidentEventPayload {
  id: number;
  title?: string;
  severity?: string;
  status: string;
  device_id?: number | null;
  assigned_to_user_id?: number | null;
  resolution_notes?: string | null;
  notes?: string | null;
}

export interface RemediationStatusPayload {
  execution_id: number;
  incident_id: number;
  rule_id: number;
  action_name: string;
  status: string;
}

export interface AlertCreatedPayload {
  id: number;
  title: string;
  message: string;
  severity: string;
  category: string;
  created_at: string;
  fingerprint: string;
  data: Record<string, unknown> | null;
}

export interface WSMessage<T = unknown> {
  type: WSEventType;
  payload: T;
  timestamp: string;
}

export type WSConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
