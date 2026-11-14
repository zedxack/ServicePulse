import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  Clock,
  LifeBuoy,
  Plus,
  RefreshCw,
  Search,
} from 'lucide-react';
import { ticketsApi } from '../../shared/api/tickets';
import { CreateTicketModal } from './CreateTicketModal';
import { MetricCard } from '../../shared/components/MetricCard';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { EmptyState } from '../../shared/components/EmptyState';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';

export const HelpdeskPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedPriority, setSelectedPriority] = useState('all');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const {
    data: ticketsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['ticketsList', selectedStatus, selectedPriority],
    queryFn: () =>
      ticketsApi.listTickets({
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
        priority: selectedPriority !== 'all' ? selectedPriority : undefined,
        limit: 100,
      }),
  });

  const tickets = ticketsData || [];
  const filteredTickets = tickets.filter((tkt) => {
    const q = searchQuery.toLowerCase();
    return (
      tkt.title.toLowerCase().includes(q) ||
      tkt.description.toLowerCase().includes(q) ||
      tkt.category.toLowerCase().includes(q)
    );
  });

  const openTickets = tickets.filter((t) => t.status === 'open' || t.status === 'in_progress').length;
  const resolvedTickets = tickets.filter((t) => t.status === 'resolved' || t.status === 'closed').length;

  const getPriorityBadge = (p: string) => {
    switch (p.toLowerCase()) {
      case 'urgent':
      case 'critical':
        return <Badge variant="offline" size="sm">{t('helpdesk.urgent')}</Badge>;
      case 'high':
        return <Badge variant="warning" size="sm">{t('helpdesk.high')}</Badge>;
      case 'medium':
        return <Badge variant="brand" size="sm">{t('helpdesk.medium')}</Badge>;
      default:
        return <Badge variant="mono" size="sm">{t('helpdesk.low')}</Badge>;
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s.toLowerCase()) {
      case 'open':
        return <Badge variant="offline" size="sm">{t('helpdesk.open')}</Badge>;
      case 'in_progress':
        return <Badge variant="brand" size="sm">{t('helpdesk.inProgress')}</Badge>;
      case 'waiting':
        return <Badge variant="warning" size="sm">{t('helpdesk.waiting')}</Badge>;
      case 'resolved':
      case 'closed':
        return <Badge variant="online" size="sm">{t('helpdesk.resolved')}</Badge>;
      default:
        return <Badge variant="mono" size="sm">{s}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('helpdesk.title')}
            </h1>
            <span className="rounded-md border border-brand-500/20 bg-brand-500/10 px-2 py-0.5 text-[11px] font-semibold text-brand-600 dark:text-brand-400">
              ITSM Service Desk
            </span>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400">{t('helpdesk.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            {t('dashboard.refresh')}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsCreateModalOpen(true)}
            leftIcon={<Plus className="h-3.5 w-3.5" />}
          >
            {t('helpdesk.newTicket')}
          </Button>
        </div>
      </div>

      {/* Counters */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <MetricCard
          title={t('helpdesk.allTickets')}
          value={isLoading ? '—' : tickets.length}
          subtitle="Cumulative tickets logged"
          icon={<LifeBuoy className="h-4 w-4" />}
          accentColor="brand"
        />
        <MetricCard
          title={t('employee.openTickets')}
          value={isLoading ? '—' : openTickets}
          subtitle="In queue & in active handling"
          icon={<Clock className="h-4 w-4" />}
          accentColor={openTickets > 0 ? 'amber' : 'brand'}
        />
        <MetricCard
          title={t('employee.resolvedTickets')}
          value={isLoading ? '—' : resolvedTickets}
          subtitle="Successfully closed tickets"
          icon={<RefreshCw className="h-4 w-4" />}
          accentColor="emerald"
        />
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-3 shadow-xs transition-colors sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 sm:max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-surface-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tickets by title, category, or description..."
            className="w-full rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 py-1.5 pl-8 pr-3 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:bg-white dark:focus:bg-surface-900 focus:outline-none transition-colors"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 px-2.5 py-1.5 text-xs font-medium text-surface-700 dark:text-surface-300 focus:outline-none"
          >
            <option value="all">{t('helpdesk.allPriorities')}</option>
            <option value="low">{t('helpdesk.low')}</option>
            <option value="medium">{t('helpdesk.medium')}</option>
            <option value="high">{t('helpdesk.high')}</option>
            <option value="urgent">{t('helpdesk.urgent')}</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 px-2.5 py-1.5 text-xs font-medium text-surface-700 dark:text-surface-300 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="open">{t('helpdesk.open')}</option>
            <option value="in_progress">{t('helpdesk.inProgress')}</option>
            <option value="waiting">{t('helpdesk.waiting')}</option>
            <option value="resolved">{t('helpdesk.resolved')}</option>
            <option value="closed">{t('helpdesk.closed')}</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-xs transition-colors">
        {isLoading ? (
          <div className="p-6 space-y-3">
            <LoadingSkeleton height="h-10" />
            <LoadingSkeleton height="h-10" />
            <LoadingSkeleton height="h-10" />
          </div>
        ) : error ? (
          <div className="p-6 text-center text-xs text-rose-600 dark:text-rose-400">
            {t('dashboard.errorLoading')}
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="py-12">
            <EmptyState
              icon={<LifeBuoy className="h-8 w-8" />}
              title={t('helpdesk.noTickets')}
              description="No tickets found matching your query or filter selections."
              action={
                <Button size="sm" onClick={() => setIsCreateModalOpen(true)}>
                  {t('helpdesk.newTicket')}
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-surface-700 dark:text-surface-300">
              <thead className="border-b border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
                <tr>
                  <th className="py-3.5 px-4">ID</th>
                  <th className="py-3.5 px-4">{t('helpdesk.priority')}</th>
                  <th className="py-3.5 px-4">{t('helpdesk.status')}</th>
                  <th className="py-3.5 px-4">{t('common.title')}</th>
                  <th className="py-3.5 px-4">{t('helpdesk.category')}</th>
                  <th className="py-3.5 px-4">{t('helpdesk.author')}</th>
                  <th className="py-3.5 px-4">Created</th>
                  <th className="py-3.5 px-4 text-right">{t('common.action')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-surface-800/80">
                {filteredTickets.map((ticket) => (
                  <tr
                    key={ticket.id}
                    className="hover:bg-surface-50/70 dark:hover:bg-surface-800/40 transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-surface-600 dark:text-surface-400">
                      #{ticket.id}
                    </td>
                    <td className="py-3.5 px-4">{getPriorityBadge(ticket.priority)}</td>
                    <td className="py-3.5 px-4">{getStatusBadge(ticket.status)}</td>
                    <td className="py-3.5 px-4 max-w-sm">
                      <p className="font-bold text-surface-900 dark:text-white truncate">{ticket.title}</p>
                      <p className="text-[11px] text-surface-500 dark:text-surface-400 truncate">
                        {ticket.description}
                      </p>
                    </td>
                    <td className="py-3.5 px-4 capitalize text-surface-600 dark:text-surface-300">
                      {ticket.category}
                    </td>
                    <td className="py-3.5 px-4 text-surface-600 dark:text-surface-400 font-mono">
                      User #{ticket.author_id}
                    </td>
                    <td className="py-3.5 px-4 text-surface-500 dark:text-surface-400 font-mono">
                      {new Date(ticket.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/tickets/${ticket.id}`)}
                      >
                        {t('incidents.details')}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {isCreateModalOpen && (
        <CreateTicketModal onClose={() => setIsCreateModalOpen(false)} />
      )}
    </div>
  );
};
