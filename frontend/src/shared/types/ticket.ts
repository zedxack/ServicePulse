export interface TicketCommentRead {
  id: number;
  ticket_id: number;
  author_id: number;
  comment: string;
  created_at: string;
}

export interface TicketCommentCreate {
  comment: string;
}

export interface TicketRead {
  id: number;
  organization_id?: number | null;
  title: string;
  description: string;
  category: string;
  priority: 'low' | 'medium' | 'high' | 'urgent' | string;
  status: 'open' | 'in_progress' | 'waiting' | 'resolved' | 'closed' | string;
  author_id: number;
  assigned_to_id?: number | null;
  device_id?: number | null;
  created_at: string;
  updated_at: string;
  comments: TicketCommentRead[];
}

export interface TicketCreate {
  title: string;
  description: string;
  category?: string;
  priority?: string;
  device_id?: number | null;
  organization_id?: number | null;
}

export interface TicketUpdate {
  title?: string;
  description?: string;
  category?: string;
  priority?: string;
  status?: string;
}

export interface TicketAssign {
  assigned_to_id: number;
}

export interface TicketResolve {
  resolution_notes?: string;
}
