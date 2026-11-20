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
  is_primary_owner?: boolean;
  organization_name?: string | null;
}

export interface UserCreatePayload {
  email: string;
  full_name: string;
  password: string;
  role_name?: string;
  role_names?: string[];
  organization_id?: number | null;
  is_active?: boolean;
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
  is_primary_owner?: boolean;
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
  role_id?: number;
  role_name?: string;
  organization_id?: number | null;
  invited_email?: string;
  max_uses?: number;
  expires_in_days?: number;
}

export interface InvitationRead {
  id: number;
  organization_id: number;
  organization_name?: string | null;
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

export interface OrganizationItem {
  id: number;
  name: string;
  slug: string;
  domain?: string | null;
  is_active: boolean;
  max_devices: number;
}

export interface InvitationCreateResponse {
  invitation: InvitationRead;
  raw_token: string;
}

export interface AccessRequestRead {
  id: number;
  request_type: string;
  status: 'pending' | 'approved' | 'rejected' | 'revoked' | string;
  applicant_email: string;
  applicant_full_name: string;
  organization_id?: number | null;
  organization_name?: string | null;
  requester_user_id?: number | null;
  target_role_name?: string | null;
  organization_request_id?: number | null;
  justification?: string | null;
  rejection_reason?: string | null;
  client_ip?: string | null;
  user_agent?: string | null;
  reviewed_by_id?: number | null;
  reviewed_at?: string | null;
  created_at: string;
}

export interface AccessRequestCreate {
  request_type: string;
  applicant_email: string;
  applicant_full_name: string;
  organization_id?: number | null;
  target_role_name?: string | null;
  justification?: string | null;
}

export interface AccessRequestStats {
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  total_count: number;
}
