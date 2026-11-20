import { apiClient } from './client';
import {
  TicketAssign,
  TicketCommentCreate,
  TicketCommentRead,
  TicketCreate,
  TicketRead,
  TicketResolve,
  TicketUpdate,
} from '../types/ticket';

export const ticketsApi = {
  listTickets: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    priority?: string;
  }): Promise<TicketRead[]> => {
    const response = await apiClient.get<TicketRead[]>('/tickets', { params });
    return response.data;
  },

  getTicket: async (ticketId: number): Promise<TicketRead> => {
    const response = await apiClient.get<TicketRead>(`/tickets/${ticketId}`);
    return response.data;
  },

  createTicket: async (data: TicketCreate): Promise<TicketRead> => {
    const response = await apiClient.post<TicketRead>('/tickets', data);
    return response.data;
  },

  updateTicket: async (ticketId: number, data: TicketUpdate): Promise<TicketRead> => {
    const response = await apiClient.patch<TicketRead>(`/tickets/${ticketId}`, data);
    return response.data;
  },

  addComment: async (ticketId: number, data: TicketCommentCreate): Promise<TicketCommentRead> => {
    const response = await apiClient.post<TicketCommentRead>(`/tickets/${ticketId}/comments`, data);
    return response.data;
  },

  getComments: async (ticketId: number): Promise<TicketCommentRead[]> => {
    const response = await apiClient.get<TicketCommentRead[]>(`/tickets/${ticketId}/comments`);
    return response.data;
  },

  assignTicket: async (ticketId: number, data: TicketAssign): Promise<TicketRead> => {
    const response = await apiClient.patch<TicketRead>(`/tickets/${ticketId}/assign`, data);
    return response.data;
  },

  resolveTicket: async (ticketId: number, data: TicketResolve): Promise<TicketRead> => {
    const response = await apiClient.patch<TicketRead>(`/tickets/${ticketId}/resolve`, data);
    return response.data;
  },
};
