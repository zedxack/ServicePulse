/**
 * ServicePulse - WebSocket Connection & Ticket API
 * Author: Muhammadyusuf Usmonov
 * Academic Purpose: AT-Servis BMI
 */
import { apiClient } from './client';
import { WSTicketResponse } from '../types/ws';

export const getWSTicket = async (): Promise<WSTicketResponse> => {
  const response = await apiClient.post<WSTicketResponse>('/ws/ticket');
  return response.data;
};

export const getWebSocketUrl = (ticket: string): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // Use host which includes hostname and port (e.g. localhost:5173 or localhost)
  const host = window.location.host;
  return `${protocol}//${host}/api/v1/ws?ticket=${encodeURIComponent(ticket)}`;
};
