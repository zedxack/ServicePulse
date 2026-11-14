import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AlertCircle, ArrowRight, CheckCircle2, Eye, EyeOff, KeyRound, Lock, Mail, ShieldCheck, User as UserIcon } from 'lucide-react';
import { useAuth } from './AuthContext';
import { authApi } from '../../shared/api/auth';
import { InvitationValidateResponse } from '../../shared/types/auth';
import { PasswordStrengthMeter } from './PasswordStrengthMeter';

interface JoinOrganizationFormProps {
  onSwitchToLogin: () => void;
}

export const JoinOrganizationForm: React.FC<JoinOrganizationFormProps> = ({ onSwitchToLogin }) => {
  const { t } = useTranslation();
  const { joinOrganization } = useAuth();
  const navigate = useNavigate();

  const [invitationCode, setInvitationCode] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [validationInfo, setValidationInfo] = useState<InvitationValidateResponse | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleValidateCode = async () => {
    const cleanCode = invitationCode.trim();
    if (!cleanCode) return;

    setIsValidating(true);
    setValidationError(null);

    try {
      const res = await authApi.validateInvitation({ invitation_code: cleanCode });
      if (res.valid) {
        setValidationInfo(res);
        if (res.invited_email && !email) {
          setEmail(res.invited_email);
        }
      } else {
        setValidationInfo(null);
        setValidationError(res.error_message || t('auth.invitationInvalid', 'Invalid or expired invitation code'));
      }
    } catch {
      setValidationInfo(null);
      setValidationError(t('auth.invitationValidateFailed', 'Failed to validate invitation code. Please check your network.'));
    } finally {
      setIsValidating(false);
    }
  };

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
      if (!joinOrganization) {
        throw new Error('Authentication provider not ready');
      }
      const user = await joinOrganization({
        invitation_code: invitationCode.trim(),
        full_name: fullName.trim(),
        email: email.trim(),
        password,
      });

      const dashboardTarget = user.primary_dashboard || 'employee';
      navigate(`/dashboard/${dashboardTarget}`, { replace: true });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const detail = axiosErr.response?.data?.detail;
      setError(detail || t('auth.registrationFailed', 'Registration failed. Please check your details.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="flex items-center gap-2.5 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Invitation Code with Inline Validation */}
      <div>
        <label className="mb-1 block text-xs font-semibold text-surface-700">
          {t('auth.invitationCodeLabel', 'Invitation Code')}
        </label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
              <KeyRound className="h-4 w-4" />
            </div>
            <input
              type="text"
              required
              value={invitationCode}
              onChange={(e) => {
                setInvitationCode(e.target.value);
                setValidationInfo(null);
                setValidationError(null);
              }}
              placeholder="sp_inv_..."
              className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm font-mono text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
            />
          </div>
          <button
            type="button"
            onClick={handleValidateCode}
            disabled={isValidating || !invitationCode.trim()}
            className="rounded-lg border border-surface-300 bg-surface-100 px-3 py-2 text-xs font-medium text-surface-700 hover:bg-surface-200 disabled:opacity-50"
          >
            {isValidating ? t('common.checking', 'Checking...') : t('common.verify', 'Verify')}
          </button>
        </div>

        {validationInfo && (
          <div className="mt-2 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-xs text-emerald-800">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 mt-0.5" />
            <div>
              <p className="font-semibold">{validationInfo.organization_name}</p>
              <p className="text-emerald-700">
                {t('auth.roleAssigned', 'Assigned role')}: <span className="font-medium capitalize">{validationInfo.role_name}</span>
              </p>
            </div>
          </div>
        )}

        {validationError && (
          <p className="mt-1 text-xs text-red-600">{validationError}</p>
        )}
      </div>

      {/* Full Name */}
      <div>
        <label className="mb-1 block text-xs font-semibold text-surface-700">
          {t('auth.fullNameLabel', 'Full Name')}
        </label>
        <div className="relative">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
            <UserIcon className="h-4 w-4" />
          </div>
          <input
            type="text"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Muhammadyusuf Usmonov"
            className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
          />
        </div>
      </div>

      {/* Email */}
      <div>
        <label className="mb-1 block text-xs font-semibold text-surface-700">
          {t('auth.emailLabel', 'Corporate Email')}
        </label>
        <div className="relative">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-surface-400">
            <Mail className="h-4 w-4" />
          </div>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@organization.uz"
            className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-3 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
          />
        </div>
      </div>

      {/* Password with Visibility Toggle & Strength Meter */}
      <div>
        <label className="mb-1 block text-xs font-semibold text-surface-700">
          {t('auth.passwordLabel', 'Password')}
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
            className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-10 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-surface-400 hover:text-surface-600"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        <PasswordStrengthMeter password={password} />
      </div>

      {/* Confirm Password */}
      <div>
        <label className="mb-1 block text-xs font-semibold text-surface-700">
          {t('auth.confirmPasswordLabel', 'Confirm Password')}
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
            className="w-full rounded-lg border border-surface-300 bg-white py-2 pl-9 pr-10 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
          />
          <button
            type="button"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-surface-400 hover:text-surface-600"
            aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
          >
            {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 disabled:opacity-60"
      >
        {isSubmitting ? (
          <span>{t('auth.joiningOrg', 'Joining Organization...')}</span>
        ) : (
          <>
            <span>{t('auth.joinOrgButton', 'Join Organization')}</span>
            <ArrowRight className="h-4 w-4" />
          </>
        )}
      </button>

      <div className="text-center pt-2">
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="text-xs text-brand-600 hover:underline font-medium"
        >
          {t('auth.alreadyHaveAccount', 'Already have an account? Sign in')}
        </button>
      </div>
    </form>
  );
};
