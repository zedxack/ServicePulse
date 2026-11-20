import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, Building2, CheckCircle2, Eye, EyeOff, Globe, Lock, Mail, Phone, ShieldCheck, User as UserIcon } from 'lucide-react';
import { authApi } from '../../shared/api/auth';
import { OrganizationRequestRead } from '../../shared/types/auth';
import { getApiErrorMessage } from '../../shared/utils/error';
import { PasswordStrengthMeter } from './PasswordStrengthMeter';

interface RegisterOrganizationFormProps {
  onSwitchToLogin: () => void;
}

export const RegisterOrganizationForm: React.FC<RegisterOrganizationFormProps> = ({ onSwitchToLogin }) => {
  const { t } = useTranslation();

  const [orgName, setOrgName] = useState('');
  const [orgEmail, setOrgEmail] = useState('');
  const [orgDomain, setOrgDomain] = useState('');
  const [phone, setPhone] = useState('');
  const [website, setWebsite] = useState('');

  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [submittedRequest, setSubmittedRequest] = useState<OrganizationRequestRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch', 'Passwords do not match'));
      return;
    }

    if (password.length < 8) {
      setError(t('auth.passwordTooShort', 'Password must be at least 8 characters long'));
      return;
    }

    setIsSubmitting(true);

    try {
      const res = await authApi.createOrganizationRequest({
        org_name: orgName.trim(),
        org_email: orgEmail.trim().toLowerCase(),
        org_domain: orgDomain.trim() ? orgDomain.trim().toLowerCase() : undefined,
        phone: phone.trim() || undefined,
        website: website.trim() || undefined,
        contact_full_name: contactName.trim(),
        contact_email: contactEmail.trim().toLowerCase(),
        password,
      });

      setSubmittedRequest(res);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, t('auth.orgRequestFailed', 'Failed to submit registration request. Please verify inputs.')));
    } finally {
      setIsSubmitting(false);
    }
  };

  // If submitted successfully, display clean pending review confirmation screen
  if (submittedRequest) {
    return (
      <div className="space-y-5 text-center py-4">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400">
          <CheckCircle2 className="h-8 w-8" />
        </div>

        <div>
          <h3 className="text-lg font-bold text-surface-900 dark:text-white">
            {t('auth.onboardingSubmittedTitle', 'Registration Request Received')}
          </h3>
          <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">
            {t('auth.onboardingSubmittedSubtitle', 'Your organization registration is currently under review by platform administrators.')}
          </p>
        </div>

        <div className="rounded-xl border border-surface-200 bg-surface-50 p-4 text-left text-xs space-y-2 dark:border-white/10 dark:bg-surface-800">
          <div className="flex justify-between">
            <span className="text-surface-500 dark:text-surface-400">{t('auth.orgNameLabel', 'Organization')}:</span>
            <span className="font-semibold text-surface-900 dark:text-white">{submittedRequest.org_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-surface-500 dark:text-surface-400">{t('auth.adminEmail', 'Admin Email')}:</span>
            <span className="font-mono text-surface-900 dark:text-white">{submittedRequest.contact_email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-surface-500 dark:text-surface-400">{t('common.status', 'Status')}:</span>
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800 uppercase tracking-wide dark:bg-amber-950/60 dark:text-amber-300">
              {submittedRequest.status}
            </span>
          </div>
        </div>

        <p className="text-xs text-surface-600 leading-relaxed dark:text-surface-400">
          {t(
            'auth.onboardingPendingNote',
            'Once verified and approved, your account will be activated with Company Administrator privileges and you can log in immediately.'
          )}
        </p>

        <button
          type="button"
          onClick={onSwitchToLogin}
          className="w-full rounded-lg bg-brand-600 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-brand-700 dark:bg-brand-600 dark:hover:bg-brand-500"
        >
          {t('auth.returnToLogin', 'Return to Sign In')}
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="flex items-center gap-2.5 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Organization Info Section */}
      <div className="border-b border-surface-200 pb-3 dark:border-white/10">
        <h4 className="text-xs font-bold uppercase tracking-wider text-surface-500 dark:text-surface-400 mb-2">
          {t('auth.organizationDetails', 'Organization Details')}
        </h4>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
              {t('auth.orgNameLabel', 'Organization Name')} *
            </label>
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                <Building2 className="h-4 w-4" />
              </div>
              <input
                type="text"
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="Example Corporation"
                className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
                {t('auth.orgEmailLabel', 'Corporate Email')} *
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="email"
                  required
                  value={orgEmail}
                  onChange={(e) => setOrgEmail(e.target.value)}
                  placeholder="contact@example.com"
                  className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
                {t('auth.orgDomainLabel', 'Corporate Domain')}
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                  <Globe className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  value={orgDomain}
                  onChange={(e) => setOrgDomain(e.target.value)}
                  placeholder="example.com"
                  className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
                {t('auth.phoneLabel', 'Phone')}
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                  <Phone className="h-4 w-4" />
                </div>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+998 71 200 00 00"
                  className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
                {t('auth.websiteLabel', 'Website')}
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                  <Globe className="h-4 w-4" />
                </div>
                <input
                  type="url"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  placeholder="https://example.com"
                  className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Administrator Section */}
      <div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-surface-500 dark:text-surface-400 mb-2">
          {t('auth.adminAccountDetails', 'Initial Administrator Account')}
        </h4>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
              {t('auth.adminFullName', 'Administrator Full Name')} *
            </label>
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                <UserIcon className="h-4 w-4" />
              </div>
              <input
                type="text"
                required
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                placeholder="Alex Morgan"
                className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
              {t('auth.adminEmail', 'Administrator Email')} *
            </label>
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                <Mail className="h-4 w-4" />
              </div>
              <input
                type="email"
                required
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                placeholder="admin@example.com"
                className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm font-mono text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
              {t('auth.passwordLabel', 'Password')} *
            </label>
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                <Lock className="h-4 w-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-10 text-sm font-mono text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-surface-400 hover:text-surface-600 dark:hover:text-surface-200"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <PasswordStrengthMeter password={password} />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
              {t('auth.confirmPasswordLabel', 'Confirm Password')} *
            </label>
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-10 text-sm font-mono text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-surface-400 hover:text-surface-600 dark:hover:text-surface-200"
              >
                {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 disabled:opacity-60 dark:bg-brand-600 dark:hover:bg-brand-500"
      >
        {isSubmitting ? (
          <span>{t('auth.submittingOrgRequest', 'Submitting Application...')}</span>
        ) : (
          <span>{t('auth.submitOrgRequestButton', 'Submit Organization Application')}</span>
        )}
      </button>

      <div className="pt-2 text-center text-xs">
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="font-medium text-brand-600 hover:underline dark:text-brand-400"
        >
          {t('auth.alreadyHaveAccount', 'Already have an account? Sign in')}
        </button>
      </div>
    </form>
  );
};
