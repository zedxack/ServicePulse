import { apiClient } from './client';
import {
  IncidentAcknowledge,
  IncidentAssign,
  IncidentCreate,
  IncidentEventRead,
  IncidentListResponse,
  IncidentRead,
  IncidentResolve,
  RemediationExecutionRead,
} from '../types/incident';

export const incidentsApi = {
  listIncidents: async (params?: {
    skip?: number;
    limit?: number;
    severity?: string;
    status?: string;
    device_id?: number;
  }): Promise<IncidentListResponse> => {
    const response = await apiClient.get<IncidentListResponse>('/incidents', { params });
    return response.data;
  },

  getIncident: async (incidentId: number): Promise<IncidentRead> => {
    const response = await apiClient.get<IncidentRead>(`/incidents/${incidentId}`);
    return response.data;
  },

  getIncidentEvents: async (incidentId: number): Promise<IncidentEventRead[]> => {
    const response = await apiClient.get<IncidentEventRead[]>(`/incidents/${incidentId}/events`);
    return response.data;
  },

  createIncident: async (data: IncidentCreate): Promise<IncidentRead> => {
    const response = await apiClient.post<IncidentRead>('/incidents', data);
    return response.data;
  },

  acknowledgeIncident: async (
    incidentId: number,
    data: IncidentAcknowledge
  ): Promise<IncidentRead> => {
    const response = await apiClient.patch<IncidentRead>(
      `/incidents/${incidentId}/acknowledge`,
      data
    );
    return response.data;
  },

  assignIncident: async (incidentId: number, data: IncidentAssign): Promise<IncidentRead> => {
    const response = await apiClient.patch<IncidentRead>(`/incidents/${incidentId}/assign`, data);
    return response.data;
  },

  resolveIncident: async (incidentId: number, data: IncidentResolve): Promise<IncidentRead> => {
    const response = await apiClient.patch<IncidentRead>(`/incidents/${incidentId}/resolve`, data);
    return response.data;
  },

  listRemediationExecutions: async (params?: {
    skip?: number;
    limit?: number;
    incident_id?: number;
  }): Promise<RemediationExecutionRead[]> => {
    const response = await apiClient.get<RemediationExecutionRead[]>('/remediations/executions', {
      params,
    });
    return response.data;
  },
};
