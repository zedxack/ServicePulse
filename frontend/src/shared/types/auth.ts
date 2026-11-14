export interface Permission {
  id: number;
  code: string;
  name: string;
  description?: string | null;
}

export interface Role {
  id: number;
  name: string;
  description?: string | null;
  permissions?: Permission[];
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  organization_id?: number | null;
  roles: Role[];
  created_at: string;
  last_login?: string | null;
  primary_dashboard: 'platform' | 'company' | 'sysadmin' | 'executive' | 'employee' | string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  primary_dashboard: string;
  organization_id?: number | null;
  full_name: string;
  roles: string[];
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface InvitationValidateRequest {
  invitation_code: string;
}

export interface InvitationValidateResponse {
  valid: boolean;
  organization_id?: number | null;
  organization_name?: string | null;
  role_id?: number | null;
  role_name?: string | null;
  invited_email?: string | null;
  error_message?: string | null;
}

export interface JoinOrganizationRequest {
  invitation_code: string;
  full_name: string;
  email: string;
  password: string;
}

export interface OrganizationRequestCreate {
  org_name: string;
  org_slug?: string;
  org_email: string;
  org_domain?: string;
  contact_full_name: string;
  contact_email: string;
  password: string;
  phone?: string;
  website?: string;
}

export interface OrganizationRequestRead {
  id: number;
  org_name: string;
  org_slug: string;
  org_email: string;
  org_domain?: string | null;
  contact_full_name: string;
  contact_email: string;
  phone?: string | null;
  website?: string | null;
  status: 'pending' | 'approved' | 'rejected' | string;
  rejection_reason?: string | null;
  reviewed_at?: string | null;
  reviewed_by_id?: number | null;
  created_organization_id?: number | null;
  created_user_id?: number | null;
  created_at: string;
}

export interface InvitationCreate {
  role_id: number;
  organization_id?: number;
  invited_email?: string;
  max_uses?: number;
  expires_in_days?: number;
}

export interface InvitationRead {
  id: number;
  organization_id: number;
  role_id: number;
  role_name?: string | null;
  token_prefix: string;
  max_uses: number;
  uses_count: number;
  expires_at: string;
  is_revoked: boolean;
  is_valid: boolean;
  invited_email?: string | null;
  created_at: string;
}

export interface InvitationCreateResponse {
  invitation: InvitationRead;
  raw_token: string;
}
