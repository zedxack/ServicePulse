/**
 * ServicePulse - In-App Alert Center Page
 * Author: Muhammadyusuf Usmonov
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  BellOff,
  Check,
  CheckCheck,
  ExternalLink,
  RefreshCw,
  Radio,
} from 'lucide-react';
import {
  getAlerts,
  markAlertRead,
  markAllAlertsRead,
} from '../../shared/api/alerts';
import { AlertSeverity, InAppNotification } from '../../shared/types/alert';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { EmptyState } from '../../shared/components/EmptyState';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';

export const AlertCenterPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [unreadOnly, setUnreadOnly] = useState<boolean>(false);
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const {
    data: alertsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['alerts', unreadOnly, selectedSeverity, selectedCategory],
    queryFn: () =>
      getAlerts({
        unread_only: unreadOnly || undefined,
        severity: selectedSeverity !== 'all' ? selectedSeverity : undefined,
        category: selectedCategory !== 'all' ? selectedCategory : undefined,
        limit: 100,
      }),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: number) => markAlertRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['unread-alerts-count'] });
    },
  });

  const markAllMutation = useMutation({
    mutationFn: () => markAllAlertsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['unread-alerts-count'] });
    },
  });

  const notifications = alertsData?.items || [];
  const unreadCount = alertsData?.unread_count || 0;

  const getSeverityBadge = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical':
      case 'error':
        return (
          <span className="inline-flex items-center gap-1.5 font-mono">
            <span className="status-dot status-dot-critical" />
            <Badge variant="offline" size="sm">{severity.toUpperCase()}</Badge>
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1.5 font-mono">
            <span className="status-dot status-dot-warning" />
            <Badge variant="warning" size="sm">WARNING</Badge>
          </span>
        );
      case 'info':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 font-mono">
            <span className="status-dot status-dot-online" />
            <Badge variant="info" size="sm">INFO</Badge>
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <Bell className="h-6 w-6 text-brand-600 dark:text-brand-400" />
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('alerts.center_title', 'Alert & Notification Center')}
            </h1>
            <span className="telemetry-pill font-mono">
              <span className={`status-dot ${unreadCount > 0 ? 'status-dot-critical' : 'status-dot-online'}`} />
              SOC ALERT TRIAGE
            </span>
            {unreadCount > 0 && (
              <span className="rounded-full bg-rose-500 px-2.5 py-0.5 text-xs font-bold text-white shadow-xs font-mono">
                {unreadCount} {t('alerts.unread', 'unread')}
              </span>
            )}
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400 mt-0.5">
            {t(
              'alerts.center_subtitle',
              'Persistent in-app operational notifications, threshold alerts, and lifecycle changes'
            )}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="hidden sm:inline-flex items-center gap-2 rounded-lg border border-surface-200 dark:border-white/10 bg-surface-50 dark:bg-surface-900/80 px-3 py-1.5 text-xs font-mono text-surface-600 dark:text-surface-300 shadow-2xs">
            <Radio className="h-3.5 w-3.5 text-brand-500 animate-pulse" />
            <span>QUEUE: STREAM</span>
            <span className="text-surface-300 dark:text-surface-700">&bull;</span>
            <span>30d RETENTION</span>
          </div>

          {unreadCount > 0 && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => markAllMutation.mutate()}
              isLoading={markAllMutation.isPending}
              leftIcon={<CheckCheck className="h-3.5 w-3.5" />}
            >
              {t('alerts.mark_all_read', 'Mark all as read')}
            </Button>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetch()}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            {t('common.refresh', 'Refresh')}
          </Button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-surface-200 dark:border-white/10 bg-white dark:bg-surface-900 p-3 shadow-xs transition-colors text-xs">
        <div className="flex flex-wrap items-center gap-3">
          {/* Unread toggle */}
          <button
            onClick={() => setUnreadOnly(!unreadOnly)}
            className={`rounded-lg px-3 py-1.5 font-semibold border transition-colors font-mono ${
              unreadOnly
                ? 'bg-brand-500/15 text-brand-700 dark:text-brand-300 border-brand-500/30'
                : 'bg-surface-50 dark:bg-surface-800 text-surface-700 dark:text-surface-300 border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-700'
            }`}
          >
            {unreadOnly
              ? t('alerts.filter_unread_only', 'Showing: Unread Only')
              : t('alerts.filter_all_status', 'Showing: All Statuses')}
          </button>

          {/* Severity filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-surface-500 dark:text-surface-400 font-medium">
              {t('alerts.severity', 'Severity')}:
            </span>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="rounded-lg border border-surface-200 dark:border-white/10 bg-surface-50 dark:bg-surface-950/50 px-2.5 py-1 text-surface-800 dark:text-surface-200 focus:outline-none"
            >
              <option value="all">{t('common.all', 'All')}</option>
              <option value="critical">Critical</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>

          {/* Category filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-surface-500 dark:text-surface-400 font-medium">
              {t('alerts.category', 'Category')}:
            </span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="rounded-lg border border-surface-200 dark:border-white/10 bg-surface-50 dark:bg-surface-950/50 px-2.5 py-1 text-surface-800 dark:text-surface-200 focus:outline-none"
            >
              <option value="all">{t('common.all', 'All')}</option>
              <option value="device">Device</option>
              <option value="incident">Incident</option>
              <option value="remediation">Remediation</option>
              <option value="ticket">Helpdesk</option>
              <option value="system">System</option>
            </select>
          </div>
        </div>

        <div className="text-surface-400 font-mono text-[11px]">
          {t('alerts.showing_count', 'Showing {{count}} alerts', { count: notifications.length })}
        </div>
      </div>

      {/* Alert Cards List */}
      {isLoading ? (
        <div className="space-y-3">
          <LoadingSkeleton height="h-20" />
          <LoadingSkeleton height="h-20" />
          <LoadingSkeleton height="h-20" />
        </div>
      ) : notifications.length === 0 ? (
        <div className="py-12">
          <EmptyState
            icon={<BellOff className="h-8 w-8" />}
            title={t('alerts.no_alerts_found', 'No notifications matching your filter')}
            description={t('alerts.all_clear', 'All clear. You have zero unread alerts in this view.')}
          />
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((notif: InAppNotification) => {
            const incidentId = notif.data?.incident_id as number | undefined;
            const deviceId = notif.data?.device_id as number | undefined;

            return (
              <div
                key={notif.id}
                className={`noc-card p-4 transition-colors ${
                  !notif.is_read
                    ? 'border-brand-500/40 bg-brand-500/5 dark:bg-brand-950/20 shadow-xs'
                    : ''
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1">
                    {/* Unread indicator */}
                    <div className="pt-1.5 flex-shrink-0">
                      {!notif.is_read ? (
                        <span className="block h-2.5 w-2.5 rounded-full bg-brand-500 animate-pulse" />
                      ) : (
                        <span className="block h-2.5 w-2.5 rounded-full bg-surface-300 dark:bg-surface-700" />
                      )}
                    </div>

                    <div className="space-y-1 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {getSeverityBadge(notif.severity)}
                        <span className="rounded bg-surface-100 dark:bg-surface-800 px-2 py-0.5 text-[10px] font-mono font-semibold uppercase text-surface-600 dark:text-surface-400">
                          {notif.category}
                        </span>
                        <h4 className="text-xs font-bold text-surface-900 dark:text-white">
                          {notif.title}
                        </h4>
                      </div>
                      <p className="text-xs text-surface-600 dark:text-surface-300">
                        {notif.message}
                      </p>

                      {/* Contextual links */}
                      <div className="flex items-center gap-3 pt-2 text-xs">
                        {incidentId && (
                          <button
                            onClick={() => navigate(`/incidents`)}
                            className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-700 dark:text-brand-400 font-semibold font-mono"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            {t('alerts.view_incident', 'View Incident #{{id}}', { id: incidentId })}
                          </button>
                        )}
                        {deviceId && (
                          <button
                            onClick={() => navigate(`/inventory`)}
                            className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-700 dark:text-brand-400 font-semibold font-mono"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            {t('alerts.view_device', 'View Device #{{id}}', { id: deviceId })}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Timestamp & Mark Read */}
                  <div className="flex sm:flex-col items-center sm:items-end justify-between gap-2 text-xs text-surface-400 flex-shrink-0">
                    <span className="font-mono text-[11px]">{new Date(notif.created_at).toLocaleString()}</span>
                    {!notif.is_read && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => markReadMutation.mutate(notif.id)}
                        isLoading={markReadMutation.isPending}
                        title={t('alerts.mark_read', 'Mark as read')}
                        leftIcon={<Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />}
                      >
                        {t('alerts.mark_read', 'Mark as read')}
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
