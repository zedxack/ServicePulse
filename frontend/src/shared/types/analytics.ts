/**
 * ServicePulse - Analytics & SLA Types
 * Author: Muhammadyusuf Usmonov
 * Academic Purpose: AT-Servis BMI
 */

export interface SLAOverview {
  period_days: number;
  target_percent: number;
  measured_uptime_percent: number | null;
  meets_target: boolean;
  total_measurement_seconds: number;
  eligible_measurement_seconds: number;
  unmonitored_seconds: number;
  planned_maintenance_seconds: number;
  unplanned_downtime_seconds: number;
  monitored_devices_count: number;
  active_outages_count: number;
  mttr_seconds: number | null;
  mttd_seconds: number | null;
  period_start: string;
  period_end: string;
  status: 'met' | 'breached' | 'insufficient_data';
}

export interface AvailabilityTrendPoint {
  date: string;
  uptime_percent: number | null;
  eligible_seconds: number;
  downtime_seconds: number;
  outage_count: number;
  meets_sla: boolean;
}

export interface AvailabilityTrendResponse {
  period_days: number;
  target_percent: number;
  overall_uptime_percent: number | null;
  points: AvailabilityTrendPoint[];
}

export interface IncidentTrendPoint {
  date: string;
  total: number;
  critical: number;
  warning: number;
  info: number;
}

export interface IncidentTrendResponse {
  period_days: number;
  total_incidents: number;
  mttr_minutes: number | null;
  points: IncidentTrendPoint[];
}
