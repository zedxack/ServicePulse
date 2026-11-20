/**
 * ServicePulse - In-App Notifications & Alerts API Client
 * Author: Muhammadyusuf Usmonov
 *  */
import { apiClient } from './client';
import {
  InAppNotification,
  NotificationListResponse,
  UnreadCountResponse,
} from '../types/alert';

export interface AlertFilterParams {
  unread_only?: boolean;
  category?: string;
  severity?: string;
  limit?: number;
  offset?: number;
}

export const getAlerts = async (
  params?: AlertFilterParams
): Promise<NotificationListResponse> => {
  const response = await apiClient.get<NotificationListResponse>('/alerts', {
    params,
  });
  return response.data;
};

export const getUnreadAlertCount = async (): Promise<UnreadCountResponse> => {
  const response = await apiClient.get<UnreadCountResponse>('/alerts/unread-count');
  return response.data;
};

export const markAlertRead = async (
  id: number
): Promise<InAppNotification> => {
  const response = await apiClient.patch<InAppNotification>(`/alerts/${id}/read`);
  return response.data;
};

export const markAllAlertsRead = async (): Promise<{ updated_count: number }> => {
  const response = await apiClient.post<{ updated_count: number }>('/alerts/mark-all-read');
  return response.data;
};
