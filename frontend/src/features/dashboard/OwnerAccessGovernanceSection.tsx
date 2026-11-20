import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  Building2,
  Check,
  CheckCircle2,
  Clock,
  Eye,
  Filter,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  X,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { authApi } from '../../shared/api/auth';
import { AccessRequestRead, AccessRequestStats } from '../../shared/types/auth';
import { Badge } from '../../shared/components/Badge';
import { EmptyState } from '../../shared/components/EmptyState';
import { LoadingSkeleton } from '../../shared/components/LoadingSkeleton';
import { getApiErrorMessage } from '../../shared/utils/error';

export const OwnerAccessGovernanceSection: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();

  const isOwner = user?.is_primary_owner ?? user?.is_superuser ?? false;

  const [requests, setRequests] = useState<AccessRequestRead[]>([]);
  const [stats, setStats] = useState<AccessRequestStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modals
  const [inspectingRequest, setInspectingRequest] = useState<AccessRequestRead | null>(null);
  const [approvingRequest, setApprovingRequest] = useState<AccessRequestRead | null>(null);
  const [rejectingRequest, setRejectingRequest] = useState<AccessRequestRead | null>(null);
  const [rejectionReason, setRejectionReason] = useState<string>('');
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const fetchGovernanceData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reqs, st] = await Promise.all([
        authApi.listAccessRequests({
          status: statusFilter === 'all' ? undefined : statusFilter,
          type: typeFilter === 'all' ? undefined : typeFilter,
        }),
        authApi.getAccessRequestStats(),
      ]);
      setRequests(reqs);
      setStats(st);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, t('governance.errorLoading', 'Failed to load access requests.')));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, typeFilter, t]);

  useEffect(() => {
    fetchGovernanceData();
  }, [fetchGovernanceData]);

  const handleApprove = async () => {
    if (!approvingRequest) return;
    setIsProcessing(true);
    setActionError(null);
    try {
      await authApi.approveAccessRequest(approvingRequest.id);
      setActionSuccess(t('governance.approveSuccess', `Approved request for ${approvingRequest.applicant_email}`));
      setApprovingRequest(null);
      await fetchGovernanceData();
    } catch (err: unknown) {
      setActionError(getApiErrorMessage(err, t('governance.approveFailed', 'Failed to approve request.')));
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!rejectingRequest) return;
    if (!rejectionReason || rejectionReason.trim().length < 3) {
      setActionError(t('governance.reasonRequired', 'A non-empty rejection reason (at least 3 characters) is required.'));
      return;
    }
    setIsProcessing(true);
    setActionError(null);
    try {
      await authApi.rejectAccessRequest(rejectingRequest.id, rejectionReason.trim());
      setActionSuccess(t('governance.rejectSuccess', `Rejected request for ${rejectingRequest.applicant_email}`));
      setRejectingRequest(null);
      setRejectionReason('');
      await fetchGovernanceData();
    } catch (err: unknown) {
      setActionError(getApiErrorMessage(err, t('governance.rejectFailed', 'Failed to reject request.')));
    } finally {
      setIsProcessing(false);
    }
  };

  const filteredRequests = requests.filter((r) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.applicant_email.toLowerCase().includes(q) ||
      r.applicant_full_name.toLowerCase().includes(q) ||
      (r.organization_name && r.organization_name.toLowerCase().includes(q)) ||
      (r.target_role_name && r.target_role_name.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Primary Owner Authority Notice */}
      <div className={`rounded-xl border p-4 ${
        isOwner
          ? 'border-emerald-200 bg-emerald-50/70 text-emerald-900 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-200'
          : 'border-amber-200 bg-amber-50/70 text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {isOwner ? (
              <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0" />
            )}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider">
                {isOwner
                  ? t('governance.primaryOwnerActive', 'Authoritative Primary Owner Access Active')
                  : t('governance.viewerNotice', 'Standard Platform Admin View (Read Only)')}
              </h3>
              <p className="text-xs opacity-90 mt-0.5">
                {isOwner
                  ? t('governance.primaryOwnerDesc', 'You possess authoritative platform owner privileges to grant or revoke organizational access, review tenants, and assign enterprise roles.')
                  : t('governance.viewerDesc', 'Only the designated Primary Platform Owner can authoritatively approve or reject access requests and organization registrations.')}
              </p>
            </div>
          </div>
          <button
            onClick={fetchGovernanceData}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-medium text-surface-700 shadow-xs hover:bg-surface-50 transition dark:border-white/10 dark:bg-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 shrink-0"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{t('common.refresh', 'Refresh')}</span>
          </button>
        </div>
      </div>

      {/* Data Load Error Banner */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Success / Error Banners */}
      {actionSuccess && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-surface-400 hover:text-surface-600">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {actionError && (
        <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-surface-400 hover:text-surface-600">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Stats Summary Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs dark:border-white/10 dark:bg-surface-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500 dark:text-surface-400">
              {t('governance.pendingReviews', 'Pending Review')}
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {stats?.pending_count ?? 0}
            </span>
            {stats && stats.pending_count > 0 && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 animate-pulse">
                ACTION REQUIRED
              </span>
            )}
          </div>
          <p className="mt-1 text-[11px] text-surface-500 dark:text-surface-400">
            Awaiting authoritative owner decision
          </p>
        </div>

        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs dark:border-white/10 dark:bg-surface-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500 dark:text-surface-400">
              {t('governance.approvedTotal', 'Approved')}
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400">
              <Check className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {stats?.approved_count ?? 0}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-surface-500 dark:text-surface-400">
            Provisioned accounts & memberships
          </p>
        </div>

        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs dark:border-white/10 dark:bg-surface-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500 dark:text-surface-400">
              {t('governance.rejectedTotal', 'Rejected')}
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400">
              <X className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {stats?.rejected_count ?? 0}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-surface-500 dark:text-surface-400">
            Declined with audit reasoning
          </p>
        </div>

        <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-xs dark:border-white/10 dark:bg-surface-900">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-500 dark:text-surface-400">
              {t('governance.totalSubmissions', 'Total Submissions')}
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-950/50 dark:text-brand-400">
              <Shield className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold tracking-tight text-surface-900 dark:text-white">
              {stats?.total_count ?? 0}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-surface-500 dark:text-surface-400">
            Lifetime centralized access records
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 rounded-xl border border-surface-200 bg-white p-3 shadow-xs dark:border-white/10 dark:bg-surface-900 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          {/* Status filter tabs */}
          <div className="flex rounded-lg border border-surface-200 bg-surface-100 p-0.5 text-xs font-medium dark:border-white/10 dark:bg-surface-800">
            <button
              onClick={() => setStatusFilter('pending')}
              className={`rounded-md px-3 py-1 transition ${
                statusFilter === 'pending'
                  ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white font-semibold'
                  : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
              }`}
            >
              Pending ({stats?.pending_count ?? 0})
            </button>
            <button
              onClick={() => setStatusFilter('approved')}
              className={`rounded-md px-3 py-1 transition ${
                statusFilter === 'approved'
                  ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white font-semibold'
                  : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
              }`}
            >
              Approved ({stats?.approved_count ?? 0})
            </button>
            <button
              onClick={() => setStatusFilter('rejected')}
              className={`rounded-md px-3 py-1 transition ${
                statusFilter === 'rejected'
                  ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white font-semibold'
                  : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
              }`}
            >
              Rejected ({stats?.rejected_count ?? 0})
            </button>
            <button
              onClick={() => setStatusFilter('all')}
              className={`rounded-md px-3 py-1 transition ${
                statusFilter === 'all'
                  ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white font-semibold'
                  : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
              }`}
            >
              All ({stats?.total_count ?? 0})
            </button>
          </div>

          {/* Type filter dropdown */}
          <div className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-surface-50 px-2.5 py-1 text-xs dark:border-white/10 dark:bg-surface-800">
            <Filter className="h-3.5 w-3.5 text-surface-400" />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-transparent text-xs text-surface-700 outline-none dark:text-surface-300"
            >
              <option value="all">All Request Types</option>
              <option value="organization_registration">Organization Registration</option>
              <option value="organization_membership">Organization Membership</option>
              <option value="company_admin_access">Company Admin Access</option>
              <option value="it_admin_access">IT Admin Access</option>
              <option value="support_access">Support Access</option>
              <option value="employee_access">Employee Access</option>
              <option value="executive_access">Executive Access</option>
            </select>
          </div>
        </div>

        {/* Search input */}
        <div className="relative min-w-[200px] sm:w-64">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2.5 text-surface-400">
            <Search className="h-3.5 w-3.5" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search email, name, org..."
            className="w-full rounded-lg border border-surface-200 bg-white py-1.5 pl-8 pr-3 text-xs text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none dark:border-white/10 dark:bg-surface-800 dark:text-white"
          />
        </div>
      </div>

      {/* Requests Table */}
      <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs dark:border-white/10 dark:bg-surface-900">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-6 space-y-4">
              <LoadingSkeleton variant="card" count={3} />
            </div>
          ) : filteredRequests.length === 0 ? (
            <EmptyState
              icon={Clock}
              title={t('governance.noRequestsTitle', 'No access requests found')}
              description={t('governance.noRequestsDesc', 'No access requests matching current filters.')}
              className="m-8"
            />
          ) : (
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600 dark:border-white/5 dark:bg-surface-800/60 dark:text-surface-300">
                <tr>
                  <th className="px-5 py-3.5">ID</th>
                  <th className="px-5 py-3.5">{t('common.type', 'Type')}</th>
                  <th className="px-5 py-3.5">{t('common.applicant', 'Applicant')}</th>
                  <th className="px-5 py-3.5">{t('common.organization', 'Organization')}</th>
                  <th className="px-5 py-3.5">{t('common.role', 'Target Role')}</th>
                  <th className="px-5 py-3.5">{t('common.status', 'Status')}</th>
                  <th className="px-5 py-3.5">{t('common.date', 'Submitted')}</th>
                  <th className="px-5 py-3.5 text-right">{t('common.actions', 'Actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 text-surface-700 dark:divide-white/5 dark:text-surface-300">
                {filteredRequests.map((req) => (
                  <tr key={req.id} className="transition-colors hover:bg-surface-50/80 dark:hover:bg-surface-800/40">
                    <td className="px-5 py-3.5 font-mono text-surface-500 dark:text-surface-400">
                      #{req.id}
                    </td>
                    <td className="px-5 py-3.5 font-medium">
                      <span className="inline-flex items-center rounded-md bg-surface-100 px-2 py-0.5 text-[11px] font-mono text-surface-700 dark:bg-surface-800 dark:text-surface-300">
                        {req.request_type}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-surface-900 dark:text-white">
                        {req.applicant_full_name}
                      </div>
                      <div className="font-mono text-[11px] text-surface-500 dark:text-surface-400">
                        {req.applicant_email}
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      {req.organization_name ? (
                        <div className="flex items-center gap-1.5 font-medium text-surface-800 dark:text-surface-200">
                          <Building2 className="h-3.5 w-3.5 text-surface-400" />
                          <span>{req.organization_name}</span>
                        </div>
                      ) : (
                        <span className="text-surface-400 italic">New Organization</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 capitalize font-mono text-[11px] text-surface-600 dark:text-surface-400">
                      {req.target_role_name || '—'}
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge
                        variant={
                          req.status === 'approved'
                            ? 'online'
                            : req.status === 'rejected'
                            ? 'offline'
                            : 'warning'
                        }
                        size="xs"
                        dot={true}
                      >
                        {req.status.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-[11px] text-surface-500 dark:text-surface-400">
                      {new Date(req.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setInspectingRequest(req)}
                          className="rounded-md border border-surface-200 bg-white px-2.5 py-1 text-xs font-medium text-surface-700 shadow-xs hover:bg-surface-50 dark:border-white/10 dark:bg-surface-800 dark:text-surface-300 dark:hover:bg-surface-700"
                          title="Inspect Details"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </button>
                        {req.status === 'pending' && isOwner && (
                          <>
                            <button
                              onClick={() => {
                                setApprovingRequest(req);
                                setActionError(null);
                              }}
                              className="rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white shadow-xs hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500"
                              title="Approve Request"
                            >
                              <Check className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={() => {
                                setRejectingRequest(req);
                                setRejectionReason('');
                                setActionError(null);
                              }}
                              className="rounded-md bg-red-600 px-2.5 py-1 text-xs font-semibold text-white shadow-xs hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-500"
                              title="Reject Request"
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Inspect Request Modal */}
      {inspectingRequest && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="inspect-dialog-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-lg rounded-2xl border border-surface-200 bg-white p-6 shadow-2xl dark:border-white/10 dark:bg-surface-900">
            <div className="flex items-center justify-between border-b border-surface-200 pb-3 dark:border-white/10">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-brand-600 dark:text-brand-400" />
                <h3 id="inspect-dialog-title" className="text-sm font-bold text-surface-900 dark:text-white">
                  Access Request #{inspectingRequest.id} Details
                </h3>
              </div>
              <button
                onClick={() => setInspectingRequest(null)}
                className="text-surface-400 hover:text-surface-600 dark:hover:text-surface-200"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 rounded-lg bg-surface-50 p-3 dark:bg-surface-800">
                <div>
                  <span className="text-surface-500 dark:text-surface-400">Request Type:</span>
                  <p className="font-semibold text-surface-900 dark:text-white capitalize">{inspectingRequest.request_type}</p>
                </div>
                <div>
                  <span className="text-surface-500 dark:text-surface-400">Status:</span>
                  <p className="font-semibold uppercase tracking-wide text-surface-900 dark:text-white">{inspectingRequest.status}</p>
                </div>
                <div>
                  <span className="text-surface-500 dark:text-surface-400">Applicant:</span>
                  <p className="font-semibold text-surface-900 dark:text-white">{inspectingRequest.applicant_full_name}</p>
                </div>
                <div>
                  <span className="text-surface-500 dark:text-surface-400">Email:</span>
                  <p className="font-mono text-surface-900 dark:text-white">{inspectingRequest.applicant_email}</p>
                </div>
              </div>

              {inspectingRequest.organization_name && (
                <div className="rounded-lg bg-surface-50 p-3 dark:bg-surface-800">
                  <span className="text-surface-500 dark:text-surface-400">Organization:</span>
                  <p className="font-semibold text-surface-900 dark:text-white">{inspectingRequest.organization_name}</p>
                </div>
              )}

              {inspectingRequest.justification && (
                <div className="rounded-lg bg-surface-50 p-3 dark:bg-surface-800">
                  <span className="text-surface-500 dark:text-surface-400">Business Justification:</span>
                  <p className="mt-1 text-surface-800 dark:text-surface-200 leading-relaxed">{inspectingRequest.justification}</p>
                </div>
              )}

              {inspectingRequest.rejection_reason && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
                  <span className="font-bold">Rejection Reason:</span>
                  <p className="mt-1 leading-relaxed">{inspectingRequest.rejection_reason}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 text-surface-500 dark:text-surface-400 text-[11px]">
                <div>Submitted: {new Date(inspectingRequest.created_at).toLocaleString()}</div>
                {inspectingRequest.reviewed_at && (
                  <div>Reviewed: {new Date(inspectingRequest.reviewed_at).toLocaleString()}</div>
                )}
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setInspectingRequest(null)}
                className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-xs font-semibold text-surface-700 hover:bg-surface-50 dark:border-white/10 dark:bg-surface-800 dark:text-surface-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Approve Confirmation Modal */}
      {approvingRequest && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="approve-dialog-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl border border-surface-200 bg-white p-6 shadow-2xl dark:border-white/10 dark:bg-surface-900">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400">
              <UserCheck className="h-6 w-6" />
            </div>

            <div className="mt-4 text-center">
              <h3 id="approve-dialog-title" className="text-base font-bold text-surface-900 dark:text-white">
                Authoritative Approval Confirmation
              </h3>
              <p className="mt-2 text-xs text-surface-500 dark:text-surface-400">
                You are about to authorize access for <span className="font-semibold text-surface-900 dark:text-white">{approvingRequest.applicant_full_name}</span> ({approvingRequest.applicant_email}).
              </p>
            </div>

            {actionError && (
              <div className="mt-4 rounded-lg bg-red-50 p-2.5 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
                {actionError}
              </div>
            )}

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => setApprovingRequest(null)}
                className="flex-1 rounded-lg border border-surface-300 bg-white py-2 text-xs font-semibold text-surface-700 hover:bg-surface-50 dark:border-white/10 dark:bg-surface-800 dark:text-surface-300"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={handleApprove}
                className="flex-1 rounded-lg bg-emerald-600 py-2 text-xs font-semibold text-white shadow-xs hover:bg-emerald-700 disabled:opacity-60"
              >
                {isProcessing ? 'Processing...' : 'Authorize & Provision'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal with Mandatory Reason */}
      {rejectingRequest && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="reject-dialog-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
        >
          <div className="w-full max-w-md rounded-2xl border border-surface-200 bg-white p-6 shadow-2xl dark:border-white/10 dark:bg-surface-900">
            <div className="flex items-center justify-between border-b border-surface-200 pb-3 dark:border-white/10">
              <h3 id="reject-dialog-title" className="text-sm font-bold text-surface-900 dark:text-white">
                Reject Access Request #{rejectingRequest.id}
              </h3>
              <button
                onClick={() => setRejectingRequest(null)}
                className="text-surface-400 hover:text-surface-600 dark:hover:text-surface-200"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 space-y-3">
              <p className="text-xs text-surface-600 dark:text-surface-400">
                Please provide an authoritative rejection reason for <span className="font-semibold text-surface-900 dark:text-white">{rejectingRequest.applicant_email}</span>. This reason will be logged in the tamper-evident audit trail and communicated to the applicant.
              </p>

              <div>
                <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  Rejection Reason *
                </label>
                <textarea
                  required
                  rows={3}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g., Target department quota reached; invalid corporate email domain; unauthorized role elevation."
                  className="w-full rounded-lg border border-surface-300 bg-white p-2.5 text-xs text-surface-900 placeholder:text-surface-400 focus:border-red-600 focus:outline-none focus:ring-1 focus:ring-red-600 dark:border-white/10 dark:bg-surface-800 dark:text-white"
                />
                <div className="mt-1 flex justify-between text-[11px] text-surface-400">
                  <span>Minimum 3 characters</span>
                  <span>{rejectionReason.length} / 500</span>
                </div>
              </div>

              {actionError && (
                <div className="rounded-lg bg-red-50 p-2.5 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
                  {actionError}
                </div>
              )}
            </div>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => setRejectingRequest(null)}
                className="flex-1 rounded-lg border border-surface-300 bg-white py-2 text-xs font-semibold text-surface-700 hover:bg-surface-50 dark:border-white/10 dark:bg-surface-800 dark:text-surface-300"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isProcessing || rejectionReason.trim().length < 3}
                onClick={handleReject}
                className="flex-1 rounded-lg bg-red-600 py-2 text-xs font-semibold text-white shadow-xs hover:bg-red-700 disabled:opacity-60"
              >
                {isProcessing ? 'Processing...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
