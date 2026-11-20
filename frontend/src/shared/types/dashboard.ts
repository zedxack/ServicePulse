export interface AuditSummaryItem {
  id: number;
  action: string;
  target_resource: string;
  target_id?: string | null;
  status: string;
  created_at: string;
}

export interface BuildingDeviceStatus {
  building_id: number;
  building_name: string;
  total_devices: number;
  online: number;
  offline: number;
  warning: number;
}

export interface TelemetrySummary {
  avg_cpu_percent?: number | null;
  avg_ram_percent?: number | null;
  avg_disk_percent?: number | null;
  total_telemetry_records: number;
}

export interface RiskDevice {
  device_id: number;
  name: string;
  hostname: string;
  device_type: string;
  ip_address: string;
  incident_count: number;
  consecutive_failures: number;
  status: string;
}

export interface IncidentTrendItem {
  date: string;
  critical: number;
  warning: number;
  info: number;
}

export interface EmployeeTicketSummary {
  id: number;
  title: string;
  priority: string;
  status: string;
  created_at: string;
}

export interface EmployeeSoftwareSummary {
  id: number;
  software_name: string;
  status: string;
  created_at: string;
}

// 1. Platform Super Admin Dashboard
export interface PlatformDashboardResponse {
  timestamp: string;
  total_organizations: number;
  active_organizations: number;
  inactive_organizations: number;
  total_platform_users: number;
  total_platform_devices: number;
  total_platform_agents: number;
  global_active_incidents: number;
  platform_health_status: string;
  recent_global_audits: AuditSummaryItem[];
}

// 2. Company Admin Dashboard
export interface CompanyDashboardResponse {
  timestamp: string;
  organization_id: number;
  organization_name: string;
  total_users: number;
  total_devices: number;
  max_devices: number;
  device_utilization_percent: number;
  total_buildings: number;
  active_incidents: number;
  recent_org_audits: AuditSummaryItem[];
}

// 3. SysAdmin Dashboard
export interface SysAdminDashboardResponse {
  timestamp: string;
  organization_id?: number | null;
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  warning_devices: number;
  unknown_devices: number;
  active_incidents: number;
  critical_incidents: number;
  daily_incidents: number;
  agents_total: number;
  agents_active: number;
  agents_offline: number;
  devices_by_building: BuildingDeviceStatus[];
  telemetry_summary: TelemetrySummary;
  active_outages_count: number;
  pending_remediations_count: number;
  verified_remediations_count: number;
  failed_remediations_count: number;
  recent_recoveries_count: number;
}

// 4. Executive / CEO Dashboard
export interface CEODashboardResponse {
  timestamp: string;
  organization_id?: number | null;
  sla_target_percent: number;
  contractual_sla_uptime_percent?: number | null;
  contractual_sla_status: string;
  contractual_sla_achievement_percent?: number | null;
  probe_success_ratio_percent?: number | null;
  probe_success_status: string;
  current_device_snapshot_percent: number;
  infrastructure_availability_percent: number;
  mttd_minutes?: number | null;
  mttr_minutes?: number | null;
  mttd_status: string;
  mttr_status: string;
  total_incidents_period: number;
  active_risk_level: string;
  incident_trends: IncidentTrendItem[];
  top_risk_devices: RiskDevice[];
  business_impact_summary: Record<string, string>;
}

// 5. Employee Dashboard
export interface EmployeeDashboardResponse {
  timestamp: string;
  user_id: number;
  user_name: string;
  open_tickets_count: number;
  resolved_tickets_count: number;
  recent_tickets: EmployeeTicketSummary[];
  pending_software_requests_count: number;
  recent_software_requests: EmployeeSoftwareSummary[];
}
