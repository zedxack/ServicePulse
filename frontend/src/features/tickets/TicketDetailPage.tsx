import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  MessageSquare,
  RefreshCw,
  Send,
  UserCheck,
} from 'lucide-react';
import { ticketsApi } from '../../shared/api/tickets';
import { useAuth } from '../auth/AuthContext';

export const TicketDetailPage: React.FC = () => {
  const { ticketId } = useParams<{ ticketId: string }>();
  const id = Number(ticketId);
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, hasAnyRole } = useAuth();
  const queryClient = useQueryClient();

  const [commentText, setCommentText] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);

  const canManage = hasAnyRole(['platform_super_admin', 'company_admin', 'it_admin', 'support', 'admin']);

  const {
    data: ticket,
    isLoading: ticketLoading,
    error: ticketError,
  } = useQuery({
    queryKey: ['ticketDetail', id],
    queryFn: () => ticketsApi.getTicket(id),
    enabled: !!id,
  });

  const commentMutation = useMutation({
    mutationFn: (comment: string) => ticketsApi.addComment(id, { comment }),
    onSuccess: () => {
      setCommentText('');
      queryClient.invalidateQueries({ queryKey: ['ticketDetail', id] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(msg || 'Failed to post comment');
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: (newStatus: string) => ticketsApi.updateTicket(id, { status: newStatus }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ticketDetail', id] });
      queryClient.invalidateQueries({ queryKey: ['ticketsList'] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(msg || 'Failed to update ticket');
    },
  });

  const updatePriorityMutation = useMutation({
    mutationFn: (newPriority: string) => ticketsApi.updateTicket(id, { priority: newPriority }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ticketDetail', id] });
      queryClient.invalidateQueries({ queryKey: ['ticketsList'] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(msg || 'Failed to update priority');
    },
  });

  const assignToMeMutation = useMutation({
    mutationFn: () => {
      if (!user) throw new Error('User not logged in');
      return ticketsApi.assignTicket(id, { assigned_to_id: user.id });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ticketDetail', id] });
      queryClient.invalidateQueries({ queryKey: ['ticketsList'] });
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setActionError(msg || 'Failed to assign ticket');
    },
  });

  const handlePostComment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    setActionError(null);
    commentMutation.mutate(commentText.trim());
  };

  if (ticketLoading) {
    return (
      <div className="py-16 text-center text-xs text-surface-500">
        <RefreshCw className="mx-auto h-6 w-6 animate-spin text-brand-500 mb-2" />
        {t('dashboard.loading')}
      </div>
    );
  }

  if (ticketError || !ticket) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-rose-600 mb-2" />
        <h3 className="text-sm font-bold text-rose-900">{t('dashboard.errorLoading')}</h3>
        <button
          onClick={() => navigate('/tickets')}
          className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-rose-700 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Yordam xizmatiga qaytish</span>
        </button>
      </div>
    );
  }

  const getPriorityBadge = (p: string) => {
    switch (p.toLowerCase()) {
      case 'urgent':
        return (
          <span className="rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-800">
            {t('helpdesk.urgent')}
          </span>
        );
      case 'high':
        return (
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-800">
            {t('helpdesk.high')}
          </span>
        );
      case 'medium':
        return (
          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-bold text-blue-800">
            {t('helpdesk.medium')}
          </span>
        );
      default:
        return (
          <span className="rounded-full bg-surface-100 px-2.5 py-0.5 text-xs font-bold text-surface-700">
            {t('helpdesk.low')}
          </span>
        );
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s.toLowerCase()) {
      case 'open':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-700 ring-1 ring-rose-200">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            {t('helpdesk.open')}
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-200">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            {t('helpdesk.inProgress')}
          </span>
        );
      case 'waiting':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 ring-1 ring-amber-200">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {t('helpdesk.waiting')}
          </span>
        );
      case 'resolved':
      case 'closed':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t('helpdesk.resolved')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2.5 py-0.5 text-xs font-semibold text-surface-700">
            {s}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <button
          onClick={() => navigate('/tickets')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-surface-600 hover:text-surface-900"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Yordam xizmatiga qaytish</span>
        </button>

        {canManage && (
          <div className="flex items-center gap-2">
            {(!ticket.assigned_to_id || ticket.assigned_to_id !== user?.id) && (
              <button
                onClick={() => assignToMeMutation.mutate()}
                disabled={assignToMeMutation.isPending}
                className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-semibold text-surface-700 hover:bg-surface-50"
              >
                <UserCheck className="h-3.5 w-3.5 text-brand-600" />
                <span>Menga biriktirish</span>
              </button>
            )}
            {ticket.status !== 'resolved' && (
              <button
                onClick={() => updateStatusMutation.mutate('resolved')}
                disabled={updateStatusMutation.isPending}
                className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-emerald-700"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{t('helpdesk.resolveTicket')}</span>
              </button>
            )}
          </div>
        )}
      </div>

      {actionError && (
        <div className="rounded-lg bg-rose-50 p-3 text-xs font-medium text-rose-700">
          {actionError}
        </div>
      )}

      {/* Ticket Main Card */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-xs">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-xs font-bold text-surface-500">#{ticket.id}</span>
              {getPriorityBadge(ticket.priority)}
              {getStatusBadge(ticket.status)}
              <span className="rounded bg-surface-100 px-2 py-0.5 text-[11px] font-semibold capitalize text-surface-600">
                {ticket.category}
              </span>
            </div>
            <h1 className="text-lg font-bold text-surface-900">{ticket.title}</h1>
            <p className="mt-2 text-xs text-surface-700 whitespace-pre-line">{ticket.description}</p>
          </div>

          {/* Support Quick Status Changer */}
          {canManage && (
            <div className="flex flex-col gap-2 rounded-lg border border-surface-200 bg-surface-50 p-3 min-w-[180px]">
              <span className="text-[10px] font-semibold text-surface-500 uppercase tracking-wider">
                Holatni o'zgartirish
              </span>
              <select
                value={ticket.status}
                onChange={(e) => updateStatusMutation.mutate(e.target.value)}
                disabled={updateStatusMutation.isPending}
                className="rounded-md border border-surface-300 bg-white px-2 py-1 text-xs font-medium text-surface-900 focus:outline-none"
              >
                <option value="open">{t('helpdesk.open')}</option>
                <option value="in_progress">{t('helpdesk.inProgress')}</option>
                <option value="waiting">{t('helpdesk.waiting')}</option>
                <option value="resolved">{t('helpdesk.resolved')}</option>
                <option value="closed">{t('helpdesk.closed')}</option>
              </select>

              <span className="text-[10px] font-semibold text-surface-500 uppercase tracking-wider mt-1">
                Muhimlik
              </span>
              <select
                value={ticket.priority}
                onChange={(e) => updatePriorityMutation.mutate(e.target.value)}
                disabled={updatePriorityMutation.isPending}
                className="rounded-md border border-surface-300 bg-white px-2 py-1 text-xs font-medium text-surface-900 focus:outline-none"
              >
                <option value="low">{t('helpdesk.low')}</option>
                <option value="medium">{t('helpdesk.medium')}</option>
                <option value="high">{t('helpdesk.high')}</option>
                <option value="urgent">{t('helpdesk.urgent')}</option>
              </select>
            </div>
          )}
        </div>

        {/* Metadata */}
        <div className="mt-6 grid grid-cols-2 gap-4 border-t border-surface-100 pt-4 sm:grid-cols-4 text-xs">
          <div>
            <span className="text-[11px] font-medium text-surface-500">{t('helpdesk.author')}</span>
            <p className="font-semibold text-surface-900">User #{ticket.author_id}</p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500">{t('helpdesk.assignedTo')}</span>
            <p className="font-semibold text-surface-900">
              {ticket.assigned_to_id ? `User #${ticket.assigned_to_id}` : t('helpdesk.unassigned')}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500">Device ID</span>
            <p className="font-mono text-surface-900">{ticket.device_id ? `#${ticket.device_id}` : '—'}</p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500">Yaratilgan sana</span>
            <p className="font-medium text-surface-700">{new Date(ticket.created_at).toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Discussion Thread */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-xs">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquare className="h-4 w-4 text-brand-600" />
          <h3 className="text-sm font-bold text-surface-900">{t('helpdesk.comments')}</h3>
        </div>

        {/* Comment list */}
        <div className="space-y-4 mb-6">
          {!ticket.comments || ticket.comments.length === 0 ? (
            <div className="py-6 text-center text-xs text-surface-500">{t('helpdesk.noComments')}</div>
          ) : (
            ticket.comments.map((c) => (
              <div key={c.id} className="rounded-lg border border-surface-150 bg-surface-50/50 p-4">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-bold text-surface-900">User #{c.author_id}</span>
                  <span className="text-[10px] text-surface-400">
                    {new Date(c.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-surface-800 whitespace-pre-line">{c.comment}</p>
              </div>
            ))
          )}
        </div>

        {/* Comment Form */}
        <form onSubmit={handlePostComment} className="border-t border-surface-200 pt-4">
          <label className="block text-xs font-semibold text-surface-700 mb-1">
            {t('helpdesk.addComment')}
          </label>
          <div className="flex gap-2">
            <textarea
              required
              rows={2}
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder={t('helpdesk.commentPlaceholder')}
              className="flex-1 rounded-lg border border-surface-300 p-2.5 text-xs text-surface-900 focus:border-brand-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={commentMutation.isPending}
              className="self-end inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-brand-700 disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
              <span>{commentMutation.isPending ? '...' : t('helpdesk.postComment')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
