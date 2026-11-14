import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelpdeskPage } from '../features/tickets/HelpdeskPage';
import { ticketsApi } from '../shared/api/tickets';
import * as AuthContextModule from '../features/auth/AuthContext';
import '../i18n/config';

vi.mock('../shared/api/tickets', () => ({
  ticketsApi: {
    listTickets: vi.fn(),
    getTicket: vi.fn(),
    createTicket: vi.fn(),
    updateTicket: vi.fn(),
    addComment: vi.fn(),
    getComments: vi.fn(),
    assignTicket: vi.fn(),
    resolveTicket: vi.fn(),
  },
}));

describe('HelpdeskPage Component & Module 5.2.3', () => {
  let queryClient: QueryClient;

  const mockTickets = [
    {
      id: 201,
      organization_id: 1,
      title: 'Cannot connect to VPN from home',
      description: 'Connection times out after password prompt',
      category: 'network',
      priority: 'high',
      status: 'open',
      author_id: 10,
      assigned_to_id: null,
      device_id: null,
      created_at: '2026-11-14T07:00:00Z',
      updated_at: '2026-11-14T07:00:00Z',
      comments: [],
    },
    {
      id: 202,
      organization_id: 1,
      title: 'Request second monitor for Lab 204',
      description: 'Need dual display for network topology diagramming',
      category: 'hardware',
      priority: 'medium',
      status: 'resolved',
      author_id: 10,
      assigned_to_id: 1,
      device_id: 10,
      created_at: '2026-11-14T06:00:00Z',
      updated_at: '2026-11-14T06:30:00Z',
      comments: [],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 10,
        email: 'employee@servicepulse.uz',
        full_name: 'Staff Employee',
        is_active: true,
        is_superuser: false,
        roles: [{ id: 6, name: 'employee' }],
        created_at: '2026-11-14T00:00:00Z',
        primary_dashboard: 'employee',
      },
      token: 'fake-token',
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      hasRole: vi.fn().mockReturnValue(false),
      hasAnyRole: vi.fn().mockReturnValue(false),
    });

    vi.mocked(ticketsApi.listTickets).mockResolvedValue(mockTickets);
    vi.mocked(ticketsApi.createTicket).mockResolvedValue({
      id: 203,
      organization_id: 1,
      title: 'New printer paper jam',
      description: 'Jam on Floor 2 corridor printer',
      category: 'hardware',
      priority: 'low',
      status: 'open',
      author_id: 10,
      created_at: '2026-11-14T08:00:00Z',
      updated_at: '2026-11-14T08:00:00Z',
      comments: [],
    });
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <HelpdeskPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders tickets list with metadata and priority badges', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Cannot connect to VPN from home')).toBeInTheDocument();
      expect(screen.getByText('Request second monitor for Lab 204')).toBeInTheDocument();
    });

    expect(screen.getByText('#201')).toBeInTheDocument();
    expect(screen.getByText('#202')).toBeInTheDocument();
  });

  it('opens new ticket modal and submits a ticket', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Cannot connect to VPN from home')).toBeInTheDocument();
    });

    const openBtn = screen.getByRole('button', { name: /Yangi Chipta|Open New Ticket|Yangi Chipta Ochish/i });
    fireEvent.click(openBtn);

    // Modal should be visible
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Monitor yoqilmayapti/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText(/Monitor yoqilmayapti/i), {
      target: { value: 'New printer paper jam' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Muammo qachon boshlandi/i), {
      target: { value: 'Jam on Floor 2 corridor printer' },
    });

    const submitBtns = screen.getAllByRole('button', { name: /Yangi Chipta|Open New Ticket|Yangi Chipta Ochish/i });
    // Click submit in modal
    fireEvent.click(submitBtns[submitBtns.length - 1]);

    await waitFor(() => {
      expect(ticketsApi.createTicket).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'New printer paper jam',
          description: 'Jam on Floor 2 corridor printer',
        })
      );
    });
  });
});
