export interface IncidentEventRead {
  id: number;
  incident_id: number;
  event_type: string;
  message: string;
  payload?: string | null;
  created_by_user_id?: number | null;
  created_at: string;
}

export interface IncidentRead {
  id: number;
  organization_id?: number | null;
  device_id?: number | null;
  fingerprint: string;
  active_dedup_key?: string | null;
  title: string;
  description: string;
  severity: 'critical' | 'warning' | 'info' | string;
  status: 'open' | 'acknowledged' | 'in_progress' | 'resolved' | string;
  occurrence_count: number;
  first_seen_at: string;
  last_seen_at: string;
  resolved_at?: string | null;
  assigned_to_user_id?: number | null;
  resolution_notes?: string | null;
  events: IncidentEventRead[];
  created_at: string;
}

export interface IncidentListResponse {
  total: number;
  items: IncidentRead[];
}

export interface IncidentCreate {
  title: string;
  description: string;
  severity?: string;
  device_id?: number | null;
  organization_id?: number | null;
  fingerprint?: string | null;
}

export interface IncidentAssign {
  assigned_to_user_id: number;
}

export interface IncidentAcknowledge {
  notes?: string;
}

export interface IncidentResolve {
  resolution_notes: string;
}

export interface RemediationExecutionRead {
  id: number;
  rule_id: number;
  incident_id: number;
  device_id?: number | null;
  status: 'pending_approval' | 'executing' | 'success' | 'failed' | 'rejected' | string;
  verification_status: 'pending' | 'verified' | 'failed' | 'unverified' | string;
  is_simulation: boolean;
  approved_by_user_id?: number | null;
  execution_log?: string | null;
  agent_command_id?: number | null;
  created_at: string;
}
