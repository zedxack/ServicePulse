import { apiClient } from './client';
import {
  InvitationCreate,
  InvitationCreateResponse,
  InvitationRead,
  InvitationValidateRequest,
  InvitationValidateResponse,
  JoinOrganizationRequest,
  LoginCredentials,
  OrganizationRequestCreate,
  OrganizationRequestRead,
  TokenResponse,
  User,
} from '../types/auth';

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/login', credentials);
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  logout: async (): Promise<void> => {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore network errors on logout
    }
  },

  refreshToken: async (refreshToken: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken });
    return response.data;
  },

  joinOrganization: async (data: JoinOrganizationRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/join-organization', data);
    return response.data;
  },

  validateInvitation: async (data: InvitationValidateRequest): Promise<InvitationValidateResponse> => {
    const response = await apiClient.post<InvitationValidateResponse>('/auth/invitations/validate', data);
    return response.data;
  },

  createOrganizationRequest: async (data: OrganizationRequestCreate): Promise<OrganizationRequestRead> => {
    const response = await apiClient.post<OrganizationRequestRead>('/auth/organization-requests', data);
    return response.data;
  },

  createInvitation: async (data: InvitationCreate): Promise<InvitationCreateResponse> => {
    const response = await apiClient.post<InvitationCreateResponse>('/auth/invitations', data);
    return response.data;
  },

  listInvitations: async (): Promise<InvitationRead[]> => {
    const response = await apiClient.get<InvitationRead[]>('/auth/invitations');
    return response.data;
  },

  revokeInvitation: async (id: number): Promise<InvitationRead> => {
    const response = await apiClient.delete<InvitationRead>(`/auth/invitations/${id}`);
    return response.data;
  },

  listOrganizationRequests: async (status?: string): Promise<OrganizationRequestRead[]> => {
    const response = await apiClient.get<OrganizationRequestRead[]>('/platform/organization-requests', {
      params: status ? { status } : undefined,
    });
    return response.data;
  },

  approveOrganizationRequest: async (id: number): Promise<OrganizationRequestRead> => {
    const response = await apiClient.post<OrganizationRequestRead>(`/platform/organization-requests/${id}/approve`);
    return response.data;
  },

  rejectOrganizationRequest: async (id: number, reason?: string): Promise<OrganizationRequestRead> => {
    const response = await apiClient.post<OrganizationRequestRead>(`/platform/organization-requests/${id}/reject`, { reason });
    return response.data;
  },
};
