/**
 * ServicePulse - In-App Notification & Alert Types
 * Author: Muhammadyusuf Usmonov
 *  */

export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical';
export type AlertCategory = 'incident' | 'device' | 'remediation' | 'ticket' | 'system';

export interface InAppNotification {
  id: number;
  organization_id: number | null;
  user_id: number | null;
  target_role: string | null;
  title: string;
  message: string;
  severity: AlertSeverity;
  category: AlertCategory;
  fingerprint: string;
  is_read: boolean;
  is_dismissed: boolean;
  read_at: string | null;
  created_at: string;
  data: Record<string, unknown> | null;
}

export interface NotificationListResponse {
  items: InAppNotification[];
  total: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}
