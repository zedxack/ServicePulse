/**
 * ServicePulse - Analytics & SLA API Client
 * Author: Muhammadyusuf Usmonov
 *  */
import { apiClient } from './client';
import {
  AvailabilityTrendResponse,
  IncidentTrendResponse,
  SLAOverview,
} from '../types/analytics';

export const getSLAOverview = async (
  periodDays: number = 30,
  deviceId?: number
): Promise<SLAOverview> => {
  const params: Record<string, string | number> = { period_days: periodDays };
  if (deviceId !== undefined) {
    params.device_id = deviceId;
  }
  const response = await apiClient.get<SLAOverview>('/analytics/sla', { params });
  return response.data;
};

export const getAvailabilityTrend = async (
  periodDays: number = 30
): Promise<AvailabilityTrendResponse> => {
  const response = await apiClient.get<AvailabilityTrendResponse>(
    '/analytics/availability-trend',
    { params: { period_days: periodDays } }
  );
  return response.data;
};

export const getIncidentTrends = async (
  periodDays: number = 30
): Promise<IncidentTrendResponse> => {
  const response = await apiClient.get<IncidentTrendResponse>(
    '/analytics/incident-trends',
    { params: { period_days: periodDays } }
  );
  return response.data;
};
