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
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700 ring-1 ring-amber-200">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {t('softwareApproval.statusPending')}
          </span>
        );
      case 'approved':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t('softwareApproval.statusApproved')}
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-[11px] font-semibold text-rose-700 ring-1 ring-rose-200">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            {t('softwareApproval.statusRejected')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-surface-100 px-2.5 py-0.5 text-[11px] font-semibold text-surface-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-surface-900">
            {t('softwareApproval.title')}
          </h2>
          <p className="text-xs text-surface-500">{t('softwareApproval.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              refetchCatalog();
              refetchRequests();
            }}
            className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-semibold text-surface-700 shadow-xs hover:bg-surface-50"
          >
            <RefreshCw className="h-3.5 w-3.5 text-surface-500" />
            <span>{t('dashboard.refresh')}</span>
          </button>
          <button
            onClick={() => handleOpenRequest()}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-brand-700"
          >
            <Plus className="h-4 w-4" />
            <span>{t('softwareApproval.requestInstall')}</span>
          </button>
        </div>
      </div>

      {/* Security Architecture Notice */}
      <div className="flex items-start gap-3 rounded-xl border border-brand-200 bg-brand-50/70 p-4 text-xs text-brand-900">
        <ShieldCheck className="h-5 w-5 shrink-0 text-brand-600 mt-0.5" />
        <p className="leading-relaxed">{t('softwareApproval.securityNotice')}</p>
      </div>

      {/* Tabs & Filter */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 bg-white p-3 shadow-xs sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1 rounded-lg border border-surface-200 bg-surface-50 p-1 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('catalog')}
            className={`rounded-md px-3 py-1 transition ${
              activeTab === 'catalog'
                ? 'bg-white text-brand-700 shadow-xs'
                : 'text-surface-600 hover:text-surface-900'
            }`}
          >
            {t('softwareApproval.catalogTab')} ({catalog.length})
          </button>
          <button
            onClick={() => setActiveTab('requests')}
            className={`rounded-md px-3 py-1 transition ${
              activeTab === 'requests'
                ? 'bg-white text-brand-700 shadow-xs'
                : 'text-surface-600 hover:text-surface-900'
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
              placeholder="Qidirish..."
              className="w-full rounded-lg border border-surface-200 bg-surface-50 py-1.5 pl-8 pr-3 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:bg-white focus:outline-none"
            />
          </div>

          {activeTab === 'requests' && (
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="rounded-lg border border-surface-200 bg-surface-50 px-2.5 py-1.5 text-xs font-medium text-surface-700 focus:outline-none"
            >
              <option value="all">Barcha holatlar</option>
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
            <div className="py-12 text-center text-xs text-surface-500">{t('dashboard.loading')}</div>
          ) : catalogError ? (
            <div className="p-6 text-center text-xs text-rose-600">{t('dashboard.errorLoading')}</div>
          ) : filteredCatalog.length === 0 ? (
            <div className="py-12 text-center text-xs text-surface-500">{t('softwareApproval.noCatalog')}</div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {filteredCatalog.map((pkg) => (
                <div
                  key={pkg}
                  className="flex flex-col justify-between rounded-xl border border-surface-200 bg-white p-4 shadow-2xs hover:border-brand-300 hover:shadow-xs transition"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                      <Package className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-bold text-surface-900 truncate">{pkg}</h4>
                      <p className="text-[11px] text-surface-500">Korxona tomonidan tasdiqlangan</p>
                    </div>
                  </div>

                  <div className="mt-4 border-t border-surface-100 pt-3">
                    <button
                      onClick={() => handleOpenRequest(pkg)}
                      className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-brand-200 bg-brand-50/50 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-100/60 transition"
                    >
                      <DownloadCloud className="h-3.5 w-3.5" />
                      <span>{t('softwareApproval.requestInstall')}</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Requests Tab */
        <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs">
          {requestsLoading ? (
            <div className="py-12 text-center text-xs text-surface-500">{t('dashboard.loading')}</div>
          ) : requestsError ? (
            <div className="p-6 text-center text-xs text-rose-600">{t('dashboard.errorLoading')}</div>
          ) : filteredRequests.length === 0 ? (
            <div className="py-12 text-center text-xs text-surface-500">
              <Package className="mx-auto h-8 w-8 text-surface-300 mb-2" />
              <p className="font-semibold text-surface-700">{t('softwareApproval.noRequests')}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-surface-700">
                <thead className="border-b border-surface-200 bg-surface-50/75 text-[11px] font-semibold uppercase tracking-wider text-surface-500">
                  <tr>
                    <th className="py-3 px-4">ID</th>
                    <th className="py-3 px-4">{t('common.software')}</th>
                    <th className="py-3 px-4">{t('softwareApproval.targetDevice')}</th>
                    <th className="py-3 px-4">{t('softwareApproval.reason')}</th>
                    <th className="py-3 px-4">Foydalanuvchi</th>
                    <th className="py-3 px-4">{t('common.status')}</th>
                    <th className="py-3 px-4">Sana</th>
                    {canApprove && <th className="py-3 px-4 text-right">{t('common.action')}</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {filteredRequests.map((req) => (
                    <tr key={req.id} className="hover:bg-surface-50/50 transition">
                      <td className="py-3 px-4 font-mono font-bold text-surface-600">#{req.id}</td>
                      <td className="py-3 px-4 font-bold text-surface-900">
                        {req.software_name}
                        {req.software_version && (
                          <span className="ml-1 text-[10px] font-normal text-surface-500">
                            v{req.software_version}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono">Device #{req.device_id}</td>
                      <td className="py-3 px-4 max-w-xs truncate text-surface-600" title={req.reason}>
                        {req.reason}
                      </td>
                      <td className="py-3 px-4">User #{req.user_id}</td>
                      <td className="py-3 px-4">{getStatusBadge(req.status)}</td>
                      <td className="py-3 px-4 text-surface-500">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      {canApprove && (
                        <td className="py-3 px-4 text-right">
                          {req.status === 'pending' ? (
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => setReviewModalState({ request: req, action: 'approve' })}
                                className="flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700 hover:bg-emerald-100"
                              >
                                <CheckCircle2 className="h-3 w-3" />
                                <span>{t('softwareApproval.approve')}</span>
                              </button>
                              <button
                                onClick={() => setReviewModalState({ request: req, action: 'reject' })}
                                className="flex items-center gap-1 rounded-md bg-rose-50 px-2 py-1 text-[11px] font-semibold text-rose-700 hover:bg-rose-100"
                              >
                                <XCircle className="h-3 w-3" />
                                <span>{t('softwareApproval.reject')}</span>
                              </button>
                            </div>
                          ) : (
                            <span className="text-[10px] text-surface-400 italic">
                              {req.review_notes || 'Ko\'rib chiqilgan'}
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
