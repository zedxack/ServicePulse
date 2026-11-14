import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  LifeBuoy,
  Plus,
  RefreshCw,
  Search,
} from 'lucide-react';
import { ticketsApi } from '../../shared/api/tickets';
import { CreateTicketModal } from './CreateTicketModal';

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
        return (
          <span className="rounded-full bg-rose-100 px-2.5 py-0.5 text-[10px] font-bold text-rose-800">
            {t('helpdesk.urgent')}
          </span>
        );
      case 'high':
        return (
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-bold text-amber-800">
            {t('helpdesk.high')}
          </span>
        );
      case 'medium':
        return (
          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-[10px] font-bold text-blue-800">
            {t('helpdesk.medium')}
          </span>
        );
      default:
        return (
          <span className="rounded-full bg-surface-100 px-2.5 py-0.5 text-[10px] font-bold text-surface-700">
            {t('helpdesk.low')}
          </span>
        );
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s.toLowerCase()) {
      case 'open':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-[11px] font-semibold text-rose-700 ring-1 ring-rose-200">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            {t('helpdesk.open')}
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-[11px] font-semibold text-blue-700 ring-1 ring-blue-200">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            {t('helpdesk.inProgress')}
          </span>
        );
      case 'waiting':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700 ring-1 ring-amber-200">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {t('helpdesk.waiting')}
          </span>
        );
      case 'resolved':
      case 'closed':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t('helpdesk.resolved')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2.5 py-0.5 text-[11px] font-semibold text-surface-700">
            {s}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-surface-900">{t('helpdesk.title')}</h2>
          <p className="text-xs text-surface-500">{t('helpdesk.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-semibold text-surface-700 shadow-xs hover:bg-surface-50"
          >
            <RefreshCw className="h-3.5 w-3.5 text-surface-500" />
            <span>{t('dashboard.refresh')}</span>
          </button>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-brand-700"
          >
            <Plus className="h-4 w-4" />
            <span>{t('helpdesk.newTicket')}</span>
          </button>
        </div>
      </div>

      {/* Counters */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-medium text-surface-500">{t('helpdesk.allTickets')}</span>
          <p className="mt-2 text-2xl font-bold text-surface-900">{isLoading ? '—' : tickets.length}</p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-medium text-amber-600">{t('employee.openTickets')}</span>
          <p className="mt-2 text-2xl font-bold text-amber-600">{isLoading ? '—' : openTickets}</p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-medium text-emerald-600">{t('employee.resolvedTickets')}</span>
          <p className="mt-2 text-2xl font-bold text-emerald-600">{isLoading ? '—' : resolvedTickets}</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 bg-white p-3 shadow-xs sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 sm:max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-surface-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Chipta nomi yoki tavsifi bo'yicha qidirish..."
            className="w-full rounded-lg border border-surface-200 bg-surface-50 py-1.5 pl-8 pr-3 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:bg-white focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="rounded-lg border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-xs font-medium text-surface-700 focus:outline-none"
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
            className="rounded-lg border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-xs font-medium text-surface-700 focus:outline-none"
          >
            <option value="all">Barcha holatlar</option>
            <option value="open">{t('helpdesk.open')}</option>
            <option value="in_progress">{t('helpdesk.inProgress')}</option>
            <option value="waiting">{t('helpdesk.waiting')}</option>
            <option value="resolved">{t('helpdesk.resolved')}</option>
            <option value="closed">{t('helpdesk.closed')}</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs">
        {isLoading ? (
          <div className="py-12 text-center text-xs text-surface-500">{t('dashboard.loading')}</div>
        ) : error ? (
          <div className="p-6 text-center text-xs text-rose-600">{t('dashboard.errorLoading')}</div>
        ) : filteredTickets.length === 0 ? (
          <div className="py-12 text-center text-xs text-surface-500">
            <LifeBuoy className="mx-auto h-8 w-8 text-surface-300 mb-2" />
            <p className="font-semibold text-surface-700">{t('helpdesk.noTickets')}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-surface-700">
              <thead className="border-b border-surface-200 bg-surface-50/75 text-[11px] font-semibold uppercase tracking-wider text-surface-500">
                <tr>
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">{t('helpdesk.priority')}</th>
                  <th className="py-3 px-4">{t('helpdesk.status')}</th>
                  <th className="py-3 px-4">{t('common.title')}</th>
                  <th className="py-3 px-4">{t('helpdesk.category')}</th>
                  <th className="py-3 px-4">{t('helpdesk.author')}</th>
                  <th className="py-3 px-4">Sana</th>
                  <th className="py-3 px-4 text-right">{t('common.action')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {filteredTickets.map((ticket) => (
                  <tr key={ticket.id} className="hover:bg-surface-50/50 transition">
                    <td className="py-3 px-4 font-mono font-bold text-surface-600">#{ticket.id}</td>
                    <td className="py-3 px-4">{getPriorityBadge(ticket.priority)}</td>
                    <td className="py-3 px-4">{getStatusBadge(ticket.status)}</td>
                    <td className="py-3 px-4 max-w-sm">
                      <p className="font-bold text-surface-900 truncate">{ticket.title}</p>
                      <p className="text-[11px] text-surface-500 truncate">{ticket.description}</p>
                    </td>
                    <td className="py-3 px-4 capitalize">{ticket.category}</td>
                    <td className="py-3 px-4">User #{ticket.author_id}</td>
                    <td className="py-3 px-4 text-surface-500">
                      {new Date(ticket.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => navigate(`/tickets/${ticket.id}`)}
                        className="rounded-md bg-surface-100 px-2.5 py-1 text-[11px] font-semibold text-brand-700 hover:bg-brand-50"
                      >
                        {t('incidents.details')}
                      </button>
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
