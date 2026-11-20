import { apiClient } from './client';
import {
  AccessRequestCreate,
  AccessRequestRead,
  AccessRequestStats,
  InvitationCreate,
  InvitationCreateResponse,
  InvitationRead,
  InvitationValidateRequest,
  InvitationValidateResponse,
  JoinOrganizationRequest,
  LoginCredentials,
  OrganizationItem,
  OrganizationRequestCreate,
  OrganizationRequestRead,
  Role,
  TokenResponse,
  User,
  UserCreatePayload,
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

  listInvitations: async (organizationId?: number): Promise<InvitationRead[]> => {
    const response = await apiClient.get<InvitationRead[]>('/auth/invitations', {
      params: organizationId ? { organization_id: organizationId } : undefined,
    });
    return response.data;
  },

  revokeInvitation: async (id: number): Promise<InvitationRead> => {
    const response = await apiClient.delete<InvitationRead>(`/auth/invitations/${id}`);
    return response.data;
  },

  listUsers: async (skip = 0, limit = 100, organizationId?: number): Promise<User[]> => {
    const response = await apiClient.get<User[]>('/auth/users', {
      params: {
        skip,
        limit,
        organization_id: organizationId || undefined,
      },
    });
    return response.data;
  },

  createUser: async (data: UserCreatePayload): Promise<User> => {
    const response = await apiClient.post<User>('/auth/users', data);
    return response.data;
  },

  updateUserStatus: async (userId: number, isActive: boolean): Promise<User> => {
    const response = await apiClient.patch<User>(`/auth/users/${userId}/status`, { is_active: isActive });
    return response.data;
  },

  listRoles: async (): Promise<Role[]> => {
    const response = await apiClient.get<Role[]>('/auth/roles');
    return response.data;
  },

  listOrganizations: async (): Promise<OrganizationItem[]> => {
    const response = await apiClient.get<OrganizationItem[]>('/organizations');
    return response.data;
  },

  getOrganization: async (id: number): Promise<OrganizationItem> => {
    const response = await apiClient.get<OrganizationItem>(`/organizations/${id}`);
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

  listAccessRequests: async (params?: { status?: string; type?: string; skip?: number; limit?: number }): Promise<AccessRequestRead[]> => {
    const response = await apiClient.get<AccessRequestRead[]>('/access-requests', { params });
    return response.data;
  },

  getAccessRequestStats: async (): Promise<AccessRequestStats> => {
    const response = await apiClient.get<AccessRequestStats>('/access-requests/stats');
    return response.data;
  },

  getAccessRequest: async (id: number): Promise<AccessRequestRead> => {
    const response = await apiClient.get<AccessRequestRead>(`/access-requests/${id}`);
    return response.data;
  },

  createAccessRequest: async (data: AccessRequestCreate): Promise<AccessRequestRead> => {
    const response = await apiClient.post<AccessRequestRead>('/access-requests', data);
    return response.data;
  },

  approveAccessRequest: async (id: number): Promise<AccessRequestRead> => {
    const response = await apiClient.post<AccessRequestRead>(`/access-requests/${id}/approve`);
    return response.data;
  },

  rejectAccessRequest: async (id: number, reason: string): Promise<AccessRequestRead> => {
    const response = await apiClient.post<AccessRequestRead>(`/access-requests/${id}/reject`, { reason });
    return response.data;
  },
};
