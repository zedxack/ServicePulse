import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  MessageSquare,
  Send,
  UserCheck,
} from 'lucide-react';
import { ticketsApi } from '../../shared/api/tickets';
import { useAuth } from '../auth/AuthContext';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';

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
      <div className="space-y-6">
        <LoadingSkeleton height="h-8" width="w-48" />
        <LoadingSkeleton height="h-64" />
        <LoadingSkeleton height="h-48" />
      </div>
    );
  }

  if (ticketError || !ticket) {
    return (
      <div className="rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/20 p-6 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-rose-600 dark:text-rose-400 mb-2" />
        <h3 className="text-sm font-bold text-rose-900 dark:text-rose-200">{t('dashboard.errorLoading')}</h3>
        <button
          onClick={() => navigate('/tickets')}
          className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-rose-700 dark:text-rose-300 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Helpdesk</span>
        </button>
      </div>
    );
  }

  const getPriorityBadge = (p: string) => {
    switch (p.toLowerCase()) {
      case 'urgent':
      case 'critical':
        return <Badge variant="offline" size="md">{t('helpdesk.urgent')}</Badge>;
      case 'high':
        return <Badge variant="warning" size="md">{t('helpdesk.high')}</Badge>;
      case 'medium':
        return <Badge variant="brand" size="md">{t('helpdesk.medium')}</Badge>;
      default:
        return <Badge variant="mono" size="md">{t('helpdesk.low')}</Badge>;
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s.toLowerCase()) {
      case 'open':
        return <Badge variant="offline" size="md">{t('helpdesk.open')}</Badge>;
      case 'in_progress':
        return <Badge variant="brand" size="md">{t('helpdesk.inProgress')}</Badge>;
      case 'waiting':
        return <Badge variant="warning" size="md">{t('helpdesk.waiting')}</Badge>;
      case 'resolved':
      case 'closed':
        return <Badge variant="online" size="md">{t('helpdesk.resolved')}</Badge>;
      default:
        return <Badge variant="mono" size="md">{s}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <button
          onClick={() => navigate('/tickets')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Helpdesk</span>
        </button>

        {canManage && (
          <div className="flex items-center gap-2">
            {(!ticket.assigned_to_id || ticket.assigned_to_id !== user?.id) && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => assignToMeMutation.mutate()}
                isLoading={assignToMeMutation.isPending}
                leftIcon={<UserCheck className="h-3.5 w-3.5" />}
              >
                Assign to Me
              </Button>
            )}
            {ticket.status !== 'resolved' && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => updateStatusMutation.mutate('resolved')}
                isLoading={updateStatusMutation.isPending}
                leftIcon={<CheckCircle2 className="h-3.5 w-3.5" />}
              >
                {t('helpdesk.resolveTicket')}
              </Button>
            )}
          </div>
        )}
      </div>

      {actionError && (
        <div className="rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-3 text-xs font-medium text-rose-700 dark:text-rose-300">
          {actionError}
        </div>
      )}

      {/* Ticket Main Card */}
      <div className="rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-6 shadow-xs transition-colors">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-xs font-bold text-surface-500 dark:text-surface-400">
                #{ticket.id}
              </span>
              {getPriorityBadge(ticket.priority)}
              {getStatusBadge(ticket.status)}
              <span className="rounded bg-surface-100 dark:bg-surface-800 px-2 py-0.5 text-[11px] font-semibold capitalize text-surface-600 dark:text-surface-400">
                {ticket.category}
              </span>
            </div>
            <h1 className="text-xl font-bold text-surface-900 dark:text-white">{ticket.title}</h1>
            <p className="mt-2 text-xs text-surface-700 dark:text-surface-300 whitespace-pre-line leading-relaxed">
              {ticket.description}
            </p>
          </div>

          {/* Support Quick Status Changer */}
          {canManage && (
            <div className="flex flex-col gap-2 rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 p-3 min-w-[180px]">
              <span className="text-[10px] font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wider">
                Status
              </span>
              <select
                value={ticket.status}
                onChange={(e) => updateStatusMutation.mutate(e.target.value)}
                disabled={updateStatusMutation.isPending}
                className="rounded-md border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-2 py-1 text-xs font-medium text-surface-900 dark:text-white focus:outline-none"
              >
                <option value="open">{t('helpdesk.open')}</option>
                <option value="in_progress">{t('helpdesk.inProgress')}</option>
                <option value="waiting">{t('helpdesk.waiting')}</option>
                <option value="resolved">{t('helpdesk.resolved')}</option>
                <option value="closed">{t('helpdesk.closed')}</option>
              </select>

              <span className="text-[10px] font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wider mt-1">
                Priority
              </span>
              <select
                value={ticket.priority}
                onChange={(e) => updatePriorityMutation.mutate(e.target.value)}
                disabled={updatePriorityMutation.isPending}
                className="rounded-md border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 px-2 py-1 text-xs font-medium text-surface-900 dark:text-white focus:outline-none"
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
        <div className="mt-6 grid grid-cols-2 gap-4 border-t border-surface-100 dark:border-surface-800 pt-4 sm:grid-cols-4 text-xs">
          <div>
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
              {t('helpdesk.author')}
            </span>
            <p className="font-semibold text-surface-900 dark:text-white">User #{ticket.author_id}</p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
              {t('helpdesk.assignedTo')}
            </span>
            <p className="font-semibold text-surface-900 dark:text-white">
              {ticket.assigned_to_id ? `User #${ticket.assigned_to_id}` : t('helpdesk.unassigned')}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">Device ID</span>
            <p className="font-mono text-surface-900 dark:text-white">
              {ticket.device_id ? `#${ticket.device_id}` : '—'}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">Created At</span>
            <p className="font-mono text-surface-700 dark:text-surface-300">
              {new Date(ticket.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Discussion Thread */}
      <div className="rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-6 shadow-xs transition-colors">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquare className="h-4 w-4 text-brand-600 dark:text-brand-400" />
          <h3 className="text-sm font-bold text-surface-900 dark:text-white">
            {t('helpdesk.comments')}
          </h3>
        </div>

        {/* Comment list */}
        <div className="space-y-4 mb-6">
          {!ticket.comments || ticket.comments.length === 0 ? (
            <div className="py-6 text-center text-xs text-surface-400">{t('helpdesk.noComments')}</div>
          ) : (
            ticket.comments.map((c) => (
              <div
                key={c.id}
                className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50/50 dark:bg-surface-950/40 p-4"
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-bold text-surface-900 dark:text-white font-mono">
                    User #{c.author_id}
                  </span>
                  <span className="text-[10px] font-mono text-surface-400">
                    {new Date(c.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-surface-800 dark:text-surface-200 whitespace-pre-line">
                  {c.comment}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Comment Form */}
        <form onSubmit={handlePostComment} className="border-t border-surface-200 dark:border-surface-800 pt-4">
          <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300 mb-1">
            {t('helpdesk.addComment')}
          </label>
          <div className="flex gap-2">
            <textarea
              required
              rows={2}
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder={t('helpdesk.commentPlaceholder')}
              className="flex-1 rounded-lg border border-surface-300 dark:border-surface-700 bg-white dark:bg-surface-800 p-2.5 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:outline-none"
            />
            <Button
              type="submit"
              variant="primary"
              size="sm"
              className="self-end"
              isLoading={commentMutation.isPending}
              leftIcon={<Send className="h-3.5 w-3.5" />}
            >
              {t('helpdesk.postComment')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
