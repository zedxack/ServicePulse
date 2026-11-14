import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import {
  CheckCircle2,
  DownloadCloud,
  Package,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { softwareApi } from '../../shared/api/software';
import { SoftwareRequestRead } from '../../shared/types/software';
import { RequestSoftwareModal } from './RequestSoftwareModal';
import { ReviewSoftwareModal } from './ReviewSoftwareModal';
import { useAuth } from '../auth/AuthContext';
import { Badge } from '../../shared/components/Badge';
import { Button } from '../../shared/components/Button';
import { EmptyState } from '../../shared/components/EmptyState';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';

export const SoftwarePage: React.FC = () => {
  const { t } = useTranslation();
  const { hasAnyRole } = useAuth();
  const [activeTab, setActiveTab] = useState<'catalog' | 'requests'>('catalog');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [isRequestModalOpen, setIsRequestModalOpen] = useState(false);
  const [preselectedPackage, setPreselectedPackage] = useState<string>('');
  const [reviewModalState, setReviewModalState] = useState<{
    request: SoftwareRequestRead;
    action: 'approve' | 'reject';
  } | null>(null);

  const canApprove = hasAnyRole(['platform_super_admin', 'company_admin', 'admin', 'it_admin']);

  const {
    data: catalog = [],
    isLoading: catalogLoading,
    error: catalogError,
    refetch: refetchCatalog,
  } = useQuery({
    queryKey: ['softwareCatalog'],
    queryFn: softwareApi.getSoftwareCatalog,
  });

  const {
    data: requests = [],
    isLoading: requestsLoading,
    error: requestsError,
    refetch: refetchRequests,
  } = useQuery({
    queryKey: ['softwareRequests', selectedStatus],
    queryFn: () =>
      softwareApi.listSoftwareRequests({
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
        limit: 100,
      }),
  });

  const filteredCatalog = catalog.filter((pkg) =>
    pkg.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredRequests = requests.filter((req) => {
    const q = searchQuery.toLowerCase();
    return (
      req.software_name.toLowerCase().includes(q) ||
      req.reason.toLowerCase().includes(q)
    );
  });

  const handleOpenRequest = (pkgName?: string) => {
    setPreselectedPackage(pkgName || '');
    setIsRequestModalOpen(true);
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending':
        return <Badge variant="warning" size="sm">{t('softwareApproval.statusPending')}</Badge>;
      case 'approved':
        return <Badge variant="online" size="sm">{t('softwareApproval.statusApproved')}</Badge>;
      case 'rejected':
        return <Badge variant="offline" size="sm">{t('softwareApproval.statusRejected')}</Badge>;
      default:
        return <Badge variant="mono" size="sm">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {t('softwareApproval.title')}
            </h1>
            <span className="rounded-md border border-brand-500/20 bg-brand-500/10 px-2 py-0.5 text-[11px] font-semibold text-brand-600 dark:text-brand-400">
              Managed Catalog
            </span>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400">{t('softwareApproval.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              refetchCatalog();
              refetchRequests();
            }}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            {t('dashboard.refresh')}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => handleOpenRequest()}
            leftIcon={<Plus className="h-3.5 w-3.5" />}
          >
            {t('softwareApproval.requestInstall')}
          </Button>
        </div>
      </div>

      {/* Security Architecture Notice */}
      <div className="flex items-start gap-3 rounded-xl border border-brand-200 dark:border-brand-800/60 bg-brand-50/70 dark:bg-brand-950/20 p-4 text-xs text-brand-900 dark:text-brand-300">
        <ShieldCheck className="h-5 w-5 shrink-0 text-brand-600 dark:text-brand-400 mt-0.5" />
        <p className="leading-relaxed">{t('softwareApproval.securityNotice')}</p>
      </div>

      {/* Tabs & Filter */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-3 shadow-xs transition-colors sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1 rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/60 p-1 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('catalog')}
            className={`rounded-md px-3 py-1 transition ${
              activeTab === 'catalog'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white'
            }`}
          >
            {t('softwareApproval.catalogTab')} ({catalog.length})
          </button>
          <button
            onClick={() => setActiveTab('requests')}
            className={`rounded-md px-3 py-1 transition ${
              activeTab === 'requests'
                ? 'bg-white dark:bg-surface-800 text-brand-700 dark:text-brand-300 shadow-xs'
                : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white'
            }`}
          >
            {t('softwareApproval.requestsTab')} ({requests.length})
          </button>
        </div>

        <div className="flex flex-1 flex-wrap items-center gap-2 sm:justify-end">
          <div className="relative min-w-[200px] flex-1 sm:max-w-xs">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-surface-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search catalog or requests..."
              className="w-full rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 py-1.5 pl-8 pr-3 text-xs text-surface-900 dark:text-white placeholder-surface-400 focus:border-brand-500 focus:bg-white dark:focus:bg-surface-900 focus:outline-none transition-colors"
            />
          </div>

          {activeTab === 'requests' && (
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50 dark:bg-surface-950/50 px-2.5 py-1.5 text-xs font-medium text-surface-700 dark:text-surface-300 focus:outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="pending">{t('softwareApproval.statusPending')}</option>
              <option value="approved">{t('softwareApproval.statusApproved')}</option>
              <option value="rejected">{t('softwareApproval.statusRejected')}</option>
            </select>
          )}
        </div>
      </div>

      {/* Content Area */}
      {activeTab === 'catalog' ? (
        <div>
          {catalogLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              <LoadingSkeleton height="h-32" />
              <LoadingSkeleton height="h-32" />
              <LoadingSkeleton height="h-32" />
              <LoadingSkeleton height="h-32" />
            </div>
          ) : catalogError ? (
            <div className="p-6 text-center text-xs text-rose-600 dark:text-rose-400">
              {t('dashboard.errorLoading')}
            </div>
          ) : filteredCatalog.length === 0 ? (
            <div className="py-12">
              <EmptyState
                icon={<Package className="h-8 w-8" />}
                title={t('softwareApproval.noCatalog')}
                description="No software packages found in the approved repository matching your search."
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {filteredCatalog.map((pkg) => (
                <div
                  key={pkg}
                  className="flex flex-col justify-between rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4 shadow-2xs hover:border-brand-400 dark:hover:border-brand-500 hover:shadow-xs transition"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-500/10 text-brand-600 dark:text-brand-400">
                      <Package className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-bold text-surface-900 dark:text-white truncate">{pkg}</h4>
                      <p className="text-[11px] text-surface-500 dark:text-surface-400">Enterprise Verified</p>
                    </div>
                  </div>

                  <div className="mt-4 border-t border-surface-100 dark:border-surface-800 pt-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full"
                      onClick={() => handleOpenRequest(pkg)}
                      leftIcon={<DownloadCloud className="h-3.5 w-3.5" />}
                    >
                      {t('softwareApproval.requestInstall')}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Requests Tab */
        <div className="overflow-hidden rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 shadow-xs transition-colors">
          {requestsLoading ? (
            <div className="p-6 space-y-3">
              <LoadingSkeleton height="h-10" />
              <LoadingSkeleton height="h-10" />
            </div>
          ) : requestsError ? (
            <div className="p-6 text-center text-xs text-rose-600 dark:text-rose-400">
              {t('dashboard.errorLoading')}
            </div>
          ) : filteredRequests.length === 0 ? (
            <div className="py-12">
              <EmptyState
                icon={<Package className="h-8 w-8" />}
                title={t('softwareApproval.noRequests')}
                description="No software installation requests have been submitted yet."
                action={
                  <Button size="sm" onClick={() => handleOpenRequest()}>
                    {t('softwareApproval.requestInstall')}
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
                    <th className="py-3.5 px-4">{t('common.software')}</th>
                    <th className="py-3.5 px-4">{t('softwareApproval.targetDevice')}</th>
                    <th className="py-3.5 px-4">{t('softwareApproval.reason')}</th>
                    <th className="py-3.5 px-4">Author</th>
                    <th className="py-3.5 px-4">{t('common.status')}</th>
                    <th className="py-3.5 px-4">Date</th>
                    {canApprove && <th className="py-3.5 px-4 text-right">{t('common.action')}</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 dark:divide-surface-800/80">
                  {filteredRequests.map((req) => (
                    <tr
                      key={req.id}
                      className="hover:bg-surface-50/70 dark:hover:bg-surface-800/40 transition-colors"
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-surface-600 dark:text-surface-400">
                        #{req.id}
                      </td>
                      <td className="py-3.5 px-4 font-bold text-surface-900 dark:text-white">
                        {req.software_name}
                        {req.software_version && (
                          <span className="ml-1 text-[10px] font-mono font-normal text-surface-500 dark:text-surface-400">
                            v{req.software_version}
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-surface-600 dark:text-surface-400">
                        Device #{req.device_id}
                      </td>
                      <td className="py-3.5 px-4 max-w-xs truncate text-surface-600 dark:text-surface-300" title={req.reason}>
                        {req.reason}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-surface-600 dark:text-surface-400">
                        User #{req.user_id}
                      </td>
                      <td className="py-3.5 px-4">{getStatusBadge(req.status)}</td>
                      <td className="py-3.5 px-4 text-surface-500 dark:text-surface-400 font-mono">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      {canApprove && (
                        <td className="py-3.5 px-4 text-right">
                          {req.status === 'pending' ? (
                            <div className="flex items-center justify-end gap-1.5">
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={() => setReviewModalState({ request: req, action: 'approve' })}
                                leftIcon={<CheckCircle2 className="h-3 w-3" />}
                              >
                                {t('softwareApproval.approve')}
                              </Button>
                              <Button
                                variant="danger"
                                size="sm"
                                onClick={() => setReviewModalState({ request: req, action: 'reject' })}
                                leftIcon={<XCircle className="h-3 w-3" />}
                              >
                                {t('softwareApproval.reject')}
                              </Button>
                            </div>
                          ) : (
                            <span className="text-[10px] text-surface-400 italic">
                              {req.review_notes || 'Reviewed'}
                            </span>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {isRequestModalOpen && (
        <RequestSoftwareModal
          initialSoftwareName={preselectedPackage}
          onClose={() => setIsRequestModalOpen(false)}
        />
      )}

      {reviewModalState && (
        <ReviewSoftwareModal
          request={reviewModalState.request}
          action={reviewModalState.action}
          onClose={() => setReviewModalState(null)}
        />
      )}
    </div>
  );
};
