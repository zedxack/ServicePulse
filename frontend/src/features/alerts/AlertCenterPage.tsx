/**
 * ServicePulse - In-App Alert Center Page
 * Author: Muhammadyusuf Usmonov
 * Academic Purpose: AT-Servis BMI
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  AlertOctagon,
  AlertTriangle,
  Bell,
  BellOff,
  Check,
  CheckCheck,
  ExternalLink,
  Info,
  RefreshCw,
} from 'lucide-react';
import {
  getAlerts,
  markAlertRead,
  markAllAlertsRead,
} from '../../shared/api/alerts';
import { AlertSeverity, InAppNotification } from '../../shared/types/alert';

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
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300">
            <AlertOctagon className="w-3.5 h-3.5" />
            CRITICAL
          </span>
        );
      case 'error':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300">
            <AlertCircle className="w-3.5 h-3.5" />
            ERROR
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5" />
            WARNING
          </span>
        );
      case 'info':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
            <Info className="w-3.5 h-3.5" />
            INFO
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Bell className="w-7 h-7 text-primary-600" />
            {t('alerts.center_title', 'Alert & Notification Center')}
            {unreadCount > 0 && (
              <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-red-600 text-white">
                {unreadCount} {t('alerts.unread', 'unread')}
              </span>
            )}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t(
              'alerts.center_subtitle',
              'Persistent in-app operational notifications, threshold alerts, and lifecycle changes'
            )}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={() => markAllMutation.mutate()}
              disabled={markAllMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-600 hover:bg-primary-700 text-white transition-colors"
            >
              <CheckCheck className="w-4 h-4" />
              {t('alerts.mark_all_read', 'Mark all as read')}
            </button>
          )}

          <button
            onClick={() => refetch()}
            className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
            title={t('common.refresh', 'Refresh')}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-wrap items-center justify-between gap-3 text-sm">
        <div className="flex flex-wrap items-center gap-3">
          {/* Unread toggle */}
          <button
            onClick={() => setUnreadOnly(!unreadOnly)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              unreadOnly
                ? 'bg-primary-50 text-primary-700 border-primary-300 dark:bg-primary-900/30 dark:text-primary-300 dark:border-primary-700'
                : 'bg-gray-50 text-gray-700 border-gray-300 dark:bg-gray-750 dark:text-gray-300 dark:border-gray-600'
            }`}
          >
            {unreadOnly
              ? t('alerts.filter_unread_only', 'Showing: Unread Only')
              : t('alerts.filter_all_status', 'Showing: All Statuses')}
          </button>

          {/* Severity filter */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">{t('alerts.severity', 'Severity')}:</span>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="text-xs border border-gray-300 dark:border-gray-600 rounded-md p-1.5 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
            >
              <option value="all">{t('common.all', 'All')}</option>
              <option value="critical">Critical</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>

          {/* Category filter */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">{t('alerts.category', 'Category')}:</span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="text-xs border border-gray-300 dark:border-gray-600 rounded-md p-1.5 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
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

        <div className="text-xs text-gray-500">
          {t('alerts.showing_count', 'Showing {{count}} alerts', { count: notifications.length })}
        </div>
      </div>

      {/* Alert Cards List */}
      {isLoading ? (
        <div className="p-12 text-center text-gray-500">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-primary-500" />
          {t('common.loading', 'Loading alerts...')}
        </div>
      ) : notifications.length === 0 ? (
        <div className="p-16 text-center bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <BellOff className="w-12 h-12 mx-auto text-gray-400 mb-3" />
          <h3 className="text-base font-semibold text-gray-800 dark:text-gray-200">
            {t('alerts.no_alerts_found', 'No notifications matching your filter')}
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {t('alerts.all_clear', 'All clear. You have zero unread alerts in this view.')}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((notif: InAppNotification) => {
            const incidentId = notif.data?.incident_id as number | undefined;
            const deviceId = notif.data?.device_id as number | undefined;

            return (
              <div
                key={notif.id}
                className={`p-4 rounded-xl border transition-colors ${
                  !notif.is_read
                    ? 'bg-blue-50/40 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900/60 shadow-sm'
                    : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1">
                    {/* Unread indicator */}
                    <div className="pt-1 flex-shrink-0">
                      {!notif.is_read ? (
                        <span
                          className="w-2.5 h-2.5 rounded-full bg-blue-600 block"
                          title="Unread"
                        />
                      ) : (
                        <span className="w-2.5 h-2.5 rounded-full bg-transparent block" />
                      )}
                    </div>

                    <div className="space-y-1 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {getSeverityBadge(notif.severity)}
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 uppercase">
                          {notif.category}
                        </span>
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                          {notif.title}
                        </h4>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-300">
                        {notif.message}
                      </p>

                      {/* Contextual links */}
                      <div className="flex items-center gap-3 pt-2 text-xs">
                        {incidentId && (
                          <button
                            onClick={() => navigate(`/incidents`)}
                            className="inline-flex items-center gap-1 text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            {t('alerts.view_incident', 'View Incident #{{id}}', { id: incidentId })}
                          </button>
                        )}
                        {deviceId && (
                          <button
                            onClick={() => navigate(`/inventory`)}
                            className="inline-flex items-center gap-1 text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            {t('alerts.view_device', 'View Device #{{id}}', { id: deviceId })}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Timestamp & Mark Read */}
                  <div className="flex sm:flex-col items-center sm:items-end justify-between gap-2 text-xs text-gray-400 flex-shrink-0">
                    <span>{new Date(notif.created_at).toLocaleString()}</span>
                    {!notif.is_read && (
                      <button
                        onClick={() => markReadMutation.mutate(notif.id)}
                        disabled={markReadMutation.isPending}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600"
                        title={t('alerts.mark_read', 'Mark as read')}
                      >
                        <Check className="w-3 h-3 text-green-600" />
                        {t('alerts.mark_read', 'Mark as read')}
                      </button>
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
