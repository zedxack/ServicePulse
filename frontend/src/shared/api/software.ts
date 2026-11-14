import { apiClient } from './client';
import {
  SoftwareRequestCreate,
  SoftwareRequestRead,
  SoftwareRequestReview,
} from '../types/software';

export const softwareApi = {
  getSoftwareCatalog: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/software/catalog');
    return response.data;
  },

  listSoftwareRequests: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<SoftwareRequestRead[]> => {
    const response = await apiClient.get<SoftwareRequestRead[]>('/software/requests', { params });
    return response.data;
  },

  getSoftwareRequest: async (requestId: number): Promise<SoftwareRequestRead> => {
    const response = await apiClient.get<SoftwareRequestRead>(`/software/requests/${requestId}`);
    return response.data;
  },

  submitSoftwareRequest: async (data: SoftwareRequestCreate): Promise<SoftwareRequestRead> => {
    const response = await apiClient.post<SoftwareRequestRead>('/software/requests', data);
    return response.data;
  },

  approveSoftwareRequest: async (
    requestId: number,
    data: SoftwareRequestReview
  ): Promise<SoftwareRequestRead> => {
    const response = await apiClient.post<SoftwareRequestRead>(
      `/software/requests/${requestId}/approve`,
      data
    );
    return response.data;
  },

  rejectSoftwareRequest: async (
    requestId: number,
    data: SoftwareRequestReview
  ): Promise<SoftwareRequestRead> => {
    const response = await apiClient.post<SoftwareRequestRead>(
      `/software/requests/${requestId}/reject`,
      data
    );
    return response.data;
  },
};
