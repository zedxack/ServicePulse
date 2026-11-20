import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  Building2,
  Check,
  CheckCircle2,
  Copy,
  Key,
  Mail,
  RefreshCw,
  Search,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { authApi } from '../../shared/api/auth';
import {
  InvitationCreate,
  InvitationRead,
  OrganizationItem,
  User,
  UserCreatePayload,
} from '../../shared/types/auth';
import { Badge, BadgeVariant } from '../../shared/components/Badge';

export interface UserAndInvitationManagementSectionProps {
  scope: 'platform' | 'company';
  currentOrganizationId?: number;
  currentOrganizationName?: string;
}

export const UserAndInvitationManagementSection: React.FC<UserAndInvitationManagementSectionProps> = ({
  scope,
  currentOrganizationId,
  currentOrganizationName,
}) => {
  const { t } = useTranslation();

  // Data states
  const [users, setUsers] = useState<User[]>([]);
  const [invitations, setInvitations] = useState<InvitationRead[]>([]);
  const [organizations, setOrganizations] = useState<OrganizationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // View state
  const [activeSubTab, setActiveSubTab] = useState<'directory' | 'invitations'>('directory');
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');

  // Modals state
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [generatedInvite, setGeneratedInvite] = useState<{ rawToken: string; details: InvitationRead } | null>(null);
  const [copiedToken, setCopiedToken] = useState(false);

  // User form state
  const [userFullName, setUserFullName] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [userPassword, setUserPassword] = useState('');
  const [userRole, setUserRole] = useState('employee');
  const [userOrgId, setUserOrgId] = useState<number>(currentOrganizationId || 1);
  const [userFormError, setUserFormError] = useState<string | null>(null);
  const [userFormSuccess, setUserFormSuccess] = useState<string | null>(null);
  const [userSubmitting, setUserSubmitting] = useState(false);

  // Invitation form state
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('support');
  const [inviteOrgId, setInviteOrgId] = useState<number>(currentOrganizationId || 1);
  const [inviteExpiryDays, setInviteExpiryDays] = useState(7);
  const [inviteMaxUses, setInviteMaxUses] = useState(1);
  const [inviteFormError, setInviteFormError] = useState<string | null>(null);
  const [inviteSubmitting, setInviteSubmitting] = useState(false);

  // Data loader
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const orgFilterParam = scope === 'company' ? currentOrganizationId : undefined;
      const [usersData, invitesData] = await Promise.all([
        authApi.listUsers(0, 200, orgFilterParam).catch(() => []),
        authApi.listInvitations(orgFilterParam).catch(() => []),
      ]);

      setUsers(usersData);
      setInvitations(invitesData);

      if (scope === 'platform') {
        const orgsData = await authApi.listOrganizations().catch(() => []);
        setOrganizations(orgsData);
        if (orgsData.length > 0 && !currentOrganizationId) {
          setUserOrgId(orgsData[0].id);
          setInviteOrgId(orgsData[0].id);
        }
      }
    } catch {
      setError(t('dashboard.errorLoading', 'Failed to load user and invitation directory'));
    } finally {
      setLoading(false);
    }
  }, [currentOrganizationId, scope, t]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Direct User Creation Handler
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setUserFormError(null);
    setUserFormSuccess(null);

    if (!userFullName.trim()) {
      setUserFormError(t('auth.nameRequired', 'Full Name is required.'));
      return;
    }
    if (!userEmail.trim()) {
      setUserFormError(t('auth.emailRequired', 'Email is required.'));
      return;
    }
    if (userPassword.length < 8) {
      setUserFormError(t('usersAndInvitations.passwordPlaceholder', 'Password must be at least 8 characters.'));
      return;
    }

    setUserSubmitting(true);
    try {
      const payload: UserCreatePayload = {
        full_name: userFullName.trim(),
        email: userEmail.trim().toLowerCase(),
        password: userPassword,
        role_name: userRole,
        organization_id: scope === 'company' ? currentOrganizationId : userOrgId,
        is_active: true,
      };

      const newUser = await authApi.createUser(payload);
      setUserFormSuccess(
        t('usersAndInvitations.userCreatedSuccess', { email: newUser.email }) ||
          `User ${newUser.email} provisioned successfully!`
      );
      setUserFullName('');
      setUserEmail('');
      setUserPassword('');
      loadData();
      setTimeout(() => {
        setIsUserModalOpen(false);
        setUserFormSuccess(null);
      }, 1800);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to provision user.';
      setUserFormError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setUserSubmitting(false);
    }
  };

  // Invitation Creation Handler
  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteFormError(null);
    setInviteSubmitting(true);

    try {
      const payload: InvitationCreate = {
        role_name: inviteRole,
        organization_id: scope === 'company' ? currentOrganizationId : inviteOrgId,
        invited_email: inviteEmail.trim() ? inviteEmail.trim().toLowerCase() : undefined,
        expires_in_days: inviteExpiryDays,
        max_uses: inviteMaxUses,
      };

      const res = await authApi.createInvitation(payload);
      const rawToken = res.raw_token || (res as any).token || '';
      const details = res.invitation || (res as any);
      setGeneratedInvite({
        rawToken,
        details,
      });
      setInviteEmail('');
      loadData();
      setIsInviteModalOpen(false);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to generate invitation.';
      setInviteFormError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setInviteSubmitting(false);
    }
  };

  // Revoke Invitation Handler
  const handleRevokeInvitation = async (invId: number) => {
    if (!window.confirm(t('common.confirmRevoke', 'Are you sure you want to revoke this invitation token?'))) {
      return;
    }
    try {
      await authApi.revokeInvitation(invId);
      loadData();
    } catch {
      alert(t('common.revokeFailed', 'Failed to revoke invitation.'));
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(true);
    setTimeout(() => setCopiedToken(false), 2500);
  };

  // Role Badge Helper
  const getRoleBadgeVariant = (roleName: string): BadgeVariant => {
    switch (roleName) {
      case 'platform_super_admin':
        return 'purple';
      case 'company_admin':
      case 'admin':
        return 'brand';
      case 'it_admin':
        return 'info';
      case 'support':
        return 'online';
      case 'executive':
        return 'warning';
      default:
        return 'default';
    }
  };

  // Filter users
  const filteredUsers = users.filter((u) => {
    const roleNames = (u.roles || []).map((r: any) =>
      typeof r === 'string' ? r : r?.name || ''
    );
    const search = searchTerm.toLowerCase();
    const matchesSearch =
      (u.full_name || '').toLowerCase().includes(search) ||
      (u.email || '').toLowerCase().includes(search) ||
      roleNames.some((rn) => rn.toLowerCase().includes(search));

    const matchesRole =
      roleFilter === 'ALL' || roleNames.includes(roleFilter);

    return matchesSearch && matchesRole;
  });

  // Filter invitations
  const filteredInvitations = invitations.filter((inv) => {
    const search = searchTerm.toLowerCase();
    const tokenStr = inv.token_prefix || (inv as any).token || '';
    const emailStr = inv.invited_email || (inv as any).email || '';
    const roleName = inv.role_name || '';

    return (
      (emailStr && emailStr.toLowerCase().includes(search)) ||
      (tokenStr && tokenStr.toLowerCase().includes(search)) ||
      (roleName && roleName.toLowerCase().includes(search))
    );
  });

  return (
    <div className="space-y-6" data-testid="user-invitation-management">
      {/* Module Header Card */}
      <div className="noc-card rounded-xl border border-surface-200 bg-white p-5 shadow-xs dark:border-white/10 dark:bg-surface-900">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-brand-200/60 bg-brand-50 text-brand-600 dark:border-brand-500/20 dark:bg-brand-950/40 dark:text-brand-400">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-surface-900 dark:text-white">
                  {t('usersAndInvitations.title', 'User & Invitation Management')}
                </h2>
                <Badge variant="brand" size="xs">
                  {scope === 'platform' ? 'CROSS-TENANT' : (currentOrganizationName || 'TENANT')}
                </Badge>
              </div>
              <p className="mt-0.5 text-xs text-surface-500 dark:text-surface-400">
                {t(
                  'usersAndInvitations.subtitle',
                  'Directly provision active credentials or generate cryptographically secure onboarding tokens'
                )}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={loadData}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs font-semibold text-surface-700 shadow-xs hover:bg-surface-50 transition dark:border-white/10 dark:bg-surface-800 dark:text-surface-300 dark:hover:bg-surface-700"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>{t('dashboard.refresh', 'Refresh')}</span>
            </button>

            <button
              type="button"
              onClick={() => setIsInviteModalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3.5 py-1.5 text-xs font-bold text-indigo-700 shadow-xs hover:bg-indigo-100 transition dark:border-indigo-500/30 dark:bg-indigo-950/50 dark:text-indigo-300 dark:hover:bg-indigo-900/60"
            >
              <Mail className="h-3.5 w-3.5" />
              <span>{t('usersAndInvitations.createInviteBtn', '+ Issue Invitation')}</span>
            </button>

            <button
              type="button"
              onClick={() => setIsUserModalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-brand-700 transition dark:bg-brand-500 dark:hover:bg-brand-600"
            >
              <UserPlus className="h-3.5 w-3.5" />
              <span>{t('usersAndInvitations.createUserBtn', '+ Create User')}</span>
            </button>
          </div>
        </div>

        {/* Telemetry Counter Pills */}
        <div className="mt-4 grid grid-cols-2 gap-3 pt-4 border-t border-surface-100 dark:border-white/5 sm:grid-cols-4">
          <div className="flex items-center justify-between rounded-lg bg-surface-50 p-2.5 dark:bg-surface-800/40 border border-surface-200/50 dark:border-white/5">
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
              {t('usersAndInvitations.totalUsers', 'Total Users')}
            </span>
            <span className="font-mono text-sm font-bold text-surface-900 dark:text-white">
              {users.length}
            </span>
          </div>

          <div className="flex items-center justify-between rounded-lg bg-surface-50 p-2.5 dark:bg-surface-800/40 border border-surface-200/50 dark:border-white/5">
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
              {t('usersAndInvitations.activeInvitations', 'Active Invitations')}
            </span>
            <span className="font-mono text-sm font-bold text-brand-600 dark:text-brand-400">
              {invitations.filter((i) => i.is_valid).length}
            </span>
          </div>

          <div className="flex items-center justify-between rounded-lg bg-surface-50 p-2.5 dark:bg-surface-800/40 border border-surface-200/50 dark:border-white/5">
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
              {scope === 'platform' ? t('usersAndInvitations.managedOrganizations', 'Organizations') : 'Current Tenant'}
            </span>
            <span className="font-mono text-sm font-bold text-purple-600 dark:text-purple-400 truncate max-w-[100px]">
              {scope === 'platform' ? organizations.length : (currentOrganizationName || 'Example Corp')}
            </span>
          </div>

          <div className="flex items-center justify-between rounded-lg bg-surface-50 p-2.5 dark:bg-surface-800/40 border border-surface-200/50 dark:border-white/5">
            <span className="text-[11px] font-medium text-surface-500 dark:text-surface-400">
              Security Protocol
            </span>
            <span className="font-mono text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
              ARGON2ID • SHA256
            </span>
          </div>
        </div>
      </div>

      {/* Generated Invitation Token Highlight Banner */}
      {generatedInvite && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50/80 p-4 shadow-sm dark:border-emerald-500/30 dark:bg-emerald-950/40 animate-in fade-in duration-300">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-emerald-950 dark:text-emerald-200">
                  {t('usersAndInvitations.inviteCreatedSuccess', 'Invitation Token Generated!')}
                </h4>
                <p className="mt-0.5 text-xs text-emerald-800 dark:text-emerald-300">
                  Share this secret token with the invitee to redeem under the{' '}
                  <span className="font-semibold underline">"Taklifnoma bilan / Join with Invite"</span> tab at /login.
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <div className="flex items-center rounded-lg border border-emerald-200 bg-white px-3 py-1.5 dark:border-emerald-800/60 dark:bg-surface-900 shadow-xs">
                    <span className="font-mono text-xs font-bold text-surface-900 dark:text-white select-all">
                      {generatedInvite.rawToken}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(generatedInvite.rawToken)}
                    className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-700 transition"
                  >
                    {copiedToken ? (
                      <>
                        <Check className="h-3.5 w-3.5" />
                        <span>{t('usersAndInvitations.copied', 'Copied!')}</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>{t('usersAndInvitations.copyToken', 'Copy Token')}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setGeneratedInvite(null)}
              className="text-emerald-600 hover:text-emerald-900 dark:text-emerald-400 dark:hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Directory vs Invitations Navigation Switcher */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex rounded-lg border border-surface-200 bg-surface-100 p-1 text-xs font-bold dark:border-white/10 dark:bg-surface-800">
          <button
            type="button"
            onClick={() => setActiveSubTab('directory')}
            className={`flex items-center gap-2 rounded-md px-3.5 py-1.5 transition-all ${
              activeSubTab === 'directory'
                ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
                : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
            }`}
          >
            <UserCheck className="h-3.5 w-3.5" />
            <span>{t('usersAndInvitations.tabDirectory', 'Active Users Directory')}</span>
            <span className="rounded-full bg-surface-200 px-1.5 py-0.2 text-[10px] dark:bg-surface-700">
              {users.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSubTab('invitations')}
            className={`flex items-center gap-2 rounded-md px-3.5 py-1.5 transition-all ${
              activeSubTab === 'invitations'
                ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
                : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
            }`}
          >
            <Mail className="h-3.5 w-3.5" />
            <span>{t('usersAndInvitations.tabInvitations', 'Issued Invitations')}</span>
            <span className="rounded-full bg-brand-100 px-1.5 py-0.2 text-[10px] text-brand-700 dark:bg-brand-950 dark:text-brand-300">
              {invitations.length}
            </span>
          </button>
        </div>

        {/* Search & Filter Controls */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-surface-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={t('usersAndInvitations.searchPlaceholder', 'Search by name, email, or role...')}
              className="w-full rounded-lg border border-surface-200 bg-white pl-8 pr-3 py-1.5 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-900 dark:text-white"
            />
          </div>

          {activeSubTab === 'directory' && (
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="rounded-lg border border-surface-200 bg-white px-2.5 py-1.5 text-xs text-surface-700 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-900 dark:text-surface-300"
            >
              <option value="ALL">{t('usersAndInvitations.filterAllRoles', 'All Roles')}</option>
              <option value="platform_super_admin">Super Admin</option>
              <option value="company_admin">Company Admin</option>
              <option value="it_admin">IT Admin</option>
              <option value="support">Support</option>
              <option value="executive">Executive</option>
              <option value="employee">Employee</option>
            </select>
          )}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-950/40 dark:text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* SUBTAB 1: Active Users Directory Table */}
      {activeSubTab === 'directory' && (
        <div className="noc-card overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs dark:border-white/10 dark:bg-surface-900">
          <div className="overflow-x-auto">
            {filteredUsers.length > 0 ? (
              <table className="w-full text-left text-xs" data-testid="active-users-table">
                <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600 dark:border-white/5 dark:bg-surface-800/60 dark:text-surface-300">
                  <tr>
                    <th className="px-5 py-3 font-mono">ID</th>
                    <th className="px-5 py-3">User & Credentials</th>
                    <th className="px-5 py-3">Assigned Roles</th>
                    <th className="px-5 py-3">Organization</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Provisioned Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 text-surface-700 dark:divide-white/5 dark:text-surface-300">
                  {filteredUsers.map((u) => (
                    <tr
                      key={u.id}
                      className="transition-colors hover:bg-surface-50/80 dark:hover:bg-surface-800/40"
                    >
                      <td className="px-5 py-3.5 font-mono text-surface-400">
                        #{u.id}
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 font-bold text-xs text-brand-700 dark:bg-brand-950 dark:text-brand-300">
                            {u.full_name ? u.full_name.charAt(0).toUpperCase() : u.email.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-surface-900 dark:text-white">
                                {u.full_name || '—'}
                              </span>
                              {u.is_primary_owner && (
                                <Badge variant="offline" size="xs">
                                  {t('usersAndInvitations.primaryOwnerBadge', 'PRIMARY OWNER')}
                                </Badge>
                              )}
                            </div>
                            <span className="font-mono text-[11px] text-surface-500 dark:text-surface-400">
                              {u.email}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex flex-wrap gap-1">
                          {u.roles && u.roles.length > 0 ? (
                            u.roles.map((r: any, idx: number) => {
                              const roleName = typeof r === 'string' ? r : r?.name || 'unknown';
                              const roleKey = typeof r === 'string' ? `${r}-${idx}` : (r?.id || `${roleName}-${idx}`);
                              return (
                                <Badge key={roleKey} variant={getRoleBadgeVariant(roleName)} size="xs">
                                  {roleName}
                                </Badge>
                              );
                            })
                          ) : (
                            <Badge variant="default" size="xs">employee</Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-1.5 font-medium text-surface-700 dark:text-surface-300">
                          <Building2 className="h-3.5 w-3.5 text-surface-400" />
                          <span>{u.organization_name || (u.organization_id ? `Org #${u.organization_id}` : 'Platform')}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge
                          variant={u.is_active ? 'online' : 'offline'}
                          size="xs"
                          dot={true}
                        >
                          {u.is_active ? t('usersAndInvitations.statusActive', 'Active') : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-[11px] text-surface-500 dark:text-surface-400">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-xs text-surface-500 dark:text-surface-400">
                {t('usersAndInvitations.emptyUsers', 'No users found matching your search filter.')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUBTAB 2: Issued Invitations Table */}
      {activeSubTab === 'invitations' && (
        <div className="noc-card overflow-hidden rounded-xl border border-surface-200 bg-white shadow-xs dark:border-white/10 dark:bg-surface-900">
          <div className="overflow-x-auto">
            {filteredInvitations.length > 0 ? (
              <table className="w-full text-left text-xs" data-testid="issued-invitations-table">
                <thead className="border-b border-surface-100 bg-surface-50 font-semibold text-surface-600 dark:border-white/5 dark:bg-surface-800/60 dark:text-surface-300">
                  <tr>
                    <th className="px-5 py-3">Token Prefix</th>
                    <th className="px-5 py-3">Invited Recipient</th>
                    <th className="px-5 py-3">Assigned Role</th>
                    <th className="px-5 py-3">Target Organization</th>
                    <th className="px-5 py-3">Usage Progress</th>
                    <th className="px-5 py-3">Expires At</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 text-surface-700 dark:divide-white/5 dark:text-surface-300">
                  {filteredInvitations.map((inv) => (
                    <tr
                      key={inv.id}
                      className="transition-colors hover:bg-surface-50/80 dark:hover:bg-surface-800/40"
                    >
                      <td className="px-5 py-3.5 font-mono font-bold text-surface-900 dark:text-white">
                        {inv.token_prefix ? `${inv.token_prefix}...` : ((inv as any).token ? `${(inv as any).token.slice(0, 14)}...` : '—')}
                      </td>
                      <td className="px-5 py-3.5">
                        {inv.invited_email ? (
                          <span className="font-mono text-surface-700 dark:text-surface-300">
                            {inv.invited_email}
                          </span>
                        ) : (
                          <span className="italic text-surface-400">
                            {t('usersAndInvitations.openInvite', 'Open / Shareable')}
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge variant={getRoleBadgeVariant(inv.role_name || '')} size="xs">
                          {inv.role_name || `Role #${inv.role_id}`}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 font-medium text-surface-600 dark:text-surface-300">
                        {inv.organization_name || `Org #${inv.organization_id}`}
                      </td>
                      <td className="px-5 py-3.5 font-mono text-[11px]">
                        {inv.uses_count ?? (inv as any).used_count ?? 0} / {inv.max_uses} max
                      </td>
                      <td className="px-5 py-3.5 font-mono text-[11px] text-surface-500 dark:text-surface-400">
                        {new Date(inv.expires_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5">
                        {inv.is_revoked ? (
                          <Badge variant="offline" size="xs">
                            {t('usersAndInvitations.statusRevoked', 'Revoked')}
                          </Badge>
                        ) : (inv.is_valid === false) ? (
                          <Badge variant="warning" size="xs">
                            {t('usersAndInvitations.statusExpired', 'Expired')}
                          </Badge>
                        ) : (
                          <Badge variant="online" size="xs" dot={true}>
                            {t('usersAndInvitations.statusActive', 'Active')}
                          </Badge>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        {!inv.is_revoked && inv.is_valid && (
                          <button
                            type="button"
                            onClick={() => handleRevokeInvitation(inv.id)}
                            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/50 transition"
                            title={t('usersAndInvitations.revoke', 'Revoke')}
                          >
                            <Trash2 className="h-3 w-3" />
                            <span>{t('usersAndInvitations.revoke', 'Revoke')}</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-xs text-surface-500 dark:text-surface-400">
                {t('usersAndInvitations.emptyInvitations', "No invitations issued yet. Click '+ Issue Invitation' to create one.")}
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 1: Direct User Account Provisioning */}
      {isUserModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="noc-panel w-full max-w-md rounded-2xl border border-surface-200 bg-white p-6 shadow-xl dark:border-white/10 dark:bg-surface-900">
            <div className="flex items-center justify-between pb-3 border-b border-surface-100 dark:border-white/5">
              <div className="flex items-center gap-2">
                <UserPlus className="h-5 w-5 text-brand-600 dark:text-brand-400" />
                <h3 className="text-sm font-bold text-surface-900 dark:text-white">
                  {t('usersAndInvitations.createUserModalTitle', 'Direct User Account Provisioning')}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsUserModalOpen(false)}
                className="text-surface-400 hover:text-surface-600 dark:hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="mt-2 text-xs text-surface-500 dark:text-surface-400">
              {t(
                'usersAndInvitations.createUserModalSubtitle',
                'Create ready-to-use login credentials that can sign in immediately at /login'
              )}
            </p>

            <form onSubmit={handleCreateUser} className="mt-4 space-y-3.5">
              {userFormError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-950/40 dark:text-red-300">
                  {userFormError}
                </div>
              )}
              {userFormSuccess && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-xs text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/40 dark:text-emerald-300">
                  {userFormSuccess}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('usersAndInvitations.fullName', 'Full Name')} *
                </label>
                <input
                  type="text"
                  required
                  value={userFullName}
                  onChange={(e) => setUserFullName(e.target.value)}
                  placeholder={t('usersAndInvitations.fullNamePlaceholder', 'e.g. John Doe / Jahongir Alimov')}
                  className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('usersAndInvitations.email', 'Email Address')} *
                </label>
                <input
                  type="email"
                  required
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  placeholder={t('usersAndInvitations.emailPlaceholder', 'user@example.com')}
                  className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('usersAndInvitations.password', 'Initial Password')} *
                </label>
                <input
                  type="password"
                  required
                  value={userPassword}
                  onChange={(e) => setUserPassword(e.target.value)}
                  placeholder={t('usersAndInvitations.passwordPlaceholder', 'Minimum 8 chars, 1 uppercase, 1 digit')}
                  className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                    {t('usersAndInvitations.role', 'Assigned Role')} *
                  </label>
                  <select
                    value={userRole}
                    onChange={(e) => setUserRole(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-2.5 py-2 text-xs text-surface-900 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white"
                  >
                    {scope === 'platform' && (
                      <option value="platform_super_admin">Platform Super Admin</option>
                    )}
                    <option value="company_admin">Company Administrator</option>
                    <option value="it_admin">IT Administrator (NOC)</option>
                    <option value="support">IT Support Engineer</option>
                    <option value="executive">Enterprise Executive</option>
                    <option value="employee">Staff / End User</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                    {t('usersAndInvitations.organization', 'Target Organization')} *
                  </label>
                  {scope === 'platform' ? (
                    <select
                      value={userOrgId}
                      onChange={(e) => setUserOrgId(Number(e.target.value))}
                      className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-2.5 py-2 text-xs text-surface-900 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white"
                    >
                      {organizations.map((org) => (
                        <option key={org.id} value={org.id}>
                          {org.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      disabled
                      value={currentOrganizationName || 'Current Organization'}
                      className="mt-1 w-full rounded-lg border border-surface-200 bg-surface-100 px-3 py-2 text-xs text-surface-600 dark:border-white/10 dark:bg-surface-800 dark:text-surface-400 font-medium"
                    />
                  )}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-surface-100 dark:border-white/5">
                <button
                  type="button"
                  onClick={() => setIsUserModalOpen(false)}
                  className="rounded-lg border border-surface-200 bg-white px-3.5 py-2 text-xs font-semibold text-surface-700 hover:bg-surface-50 dark:border-white/10 dark:bg-surface-800 dark:text-surface-300"
                >
                  {t('usersAndInvitations.cancel', 'Cancel')}
                </button>
                <button
                  type="submit"
                  disabled={userSubmitting}
                  className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-xs font-bold text-white hover:bg-brand-700 disabled:opacity-50 transition"
                >
                  {userSubmitting && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                  <span>{t('usersAndInvitations.submitCreateUser', 'Provision User')}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Cryptographic Invitation Issuance */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="noc-panel w-full max-w-md rounded-2xl border border-surface-200 bg-white p-6 shadow-xl dark:border-white/10 dark:bg-surface-900">
            <div className="flex items-center justify-between pb-3 border-b border-surface-100 dark:border-white/5">
              <div className="flex items-center gap-2">
                <Key className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                <h3 className="text-sm font-bold text-surface-900 dark:text-white">
                  {t('usersAndInvitations.createInviteModalTitle', 'Cryptographic Invitation Issuance')}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsInviteModalOpen(false)}
                className="text-surface-400 hover:text-surface-600 dark:hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="mt-2 text-xs text-surface-500 dark:text-surface-400">
              {t(
                'usersAndInvitations.createInviteModalSubtitle',
                'Generate an onboarding invite token (sp_inv_...) with scoped tenant and role assignment'
              )}
            </p>

            <form onSubmit={handleCreateInvite} className="mt-4 space-y-3.5">
              {inviteFormError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-950/40 dark:text-red-300">
                  {inviteFormError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                  {t('usersAndInvitations.restrictedEmail', 'Restricted Invitee Email (Optional)')}
                </label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder={t(
                    'usersAndInvitations.restrictedEmailPlaceholder',
                    'Leave blank for open shareable link'
                  )}
                  className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                    {t('usersAndInvitations.role', 'Assigned Role')} *
                  </label>
                  <select
                    data-testid="invite-role-select"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-2.5 py-2 text-xs text-surface-900 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white"
                  >
                    {scope === 'platform' && (
                      <option value="company_admin">Company Administrator</option>
                    )}
                    <option value="it_admin">IT Administrator (NOC)</option>
                    <option value="support">IT Support Engineer</option>
                    <option value="executive">Enterprise Executive</option>
                    <option value="employee">Staff / End User</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                    {t('usersAndInvitations.organization', 'Target Organization')} *
                  </label>
                  {scope === 'platform' ? (
                    <select
                      value={inviteOrgId}
                      onChange={(e) => setInviteOrgId(Number(e.target.value))}
                      className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-2.5 py-2 text-xs text-surface-900 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white"
                    >
                      {organizations.map((org) => (
                        <option key={org.id} value={org.id}>
                          {org.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      disabled
                      value={currentOrganizationName || 'Current Organization'}
                      className="mt-1 w-full rounded-lg border border-surface-200 bg-surface-100 px-3 py-2 text-xs text-surface-600 dark:border-white/10 dark:bg-surface-800 dark:text-surface-400 font-medium"
                    />
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                    {t('usersAndInvitations.expiryDays', 'Expiry (Days)')}
                  </label>
                  <select
                    value={inviteExpiryDays}
                    onChange={(e) => setInviteExpiryDays(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-2.5 py-2 text-xs text-surface-900 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white"
                  >
                    <option value={1}>{t('usersAndInvitations.days1', '1 Day (Immediate)')}</option>
                    <option value={3}>{t('usersAndInvitations.days3', '3 Days')}</option>
                    <option value={7}>{t('usersAndInvitations.days7', '7 Days (Standard)')}</option>
                    <option value={14}>{t('usersAndInvitations.days14', '14 Days')}</option>
                    <option value={30}>{t('usersAndInvitations.days30', '30 Days (Extended)')}</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-surface-700 dark:text-surface-300">
                    {t('usersAndInvitations.maxUses', 'Max Uses')}
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={500}
                    value={inviteMaxUses}
                    onChange={(e) => setInviteMaxUses(Math.max(1, parseInt(e.target.value) || 1))}
                    className="mt-1 w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-xs text-surface-900 focus:border-brand-500 focus:outline-hidden dark:border-white/10 dark:bg-surface-800 dark:text-white font-mono"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-surface-100 dark:border-white/5">
                <button
                  type="button"
                  onClick={() => setIsInviteModalOpen(false)}
                  className="rounded-lg border border-surface-200 bg-white px-3.5 py-2 text-xs font-semibold text-surface-700 hover:bg-surface-50 dark:border-white/10 dark:bg-surface-800 dark:text-surface-300"
                >
                  {t('usersAndInvitations.cancel', 'Cancel')}
                </button>
                <button
                  type="submit"
                  disabled={inviteSubmitting}
                  className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-700 disabled:opacity-50 transition"
                >
                  {inviteSubmitting && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                  <span>{t('usersAndInvitations.submitCreateInvite', 'Generate Token')}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
