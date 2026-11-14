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
