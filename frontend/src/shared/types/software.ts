export interface SoftwareRequestRead {
  id: number;
  organization_id?: number | null;
  user_id: number;
  device_id: number;
  software_name: string;
  software_version?: string | null;
  reason: string;
  status: 'pending' | 'approved' | 'rejected' | string;
  reviewed_by_user_id?: number | null;
  review_notes?: string | null;
  reviewed_at?: string | null;
  created_at: string;
}

export interface SoftwareRequestCreate {
  device_id: number;
  software_name: string;
  software_version?: string | null;
  reason: string;
  organization_id?: number | null;
}

export interface SoftwareRequestReview {
  review_notes?: string | null;
}
