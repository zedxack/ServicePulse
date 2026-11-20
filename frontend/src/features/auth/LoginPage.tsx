import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Activity, AlertCircle, ArrowRight, Eye, EyeOff, Lock, Mail, Shield, Sparkles } from 'lucide-react';
import { useAuth } from './AuthContext';
import { LanguageSwitcher } from '../../shared/components/LanguageSwitcher';
import { ThemeToggle } from '../../shared/components/ThemeToggle';
import { getApiErrorMessage } from '../../shared/utils/error';
import { JoinOrganizationForm } from './JoinOrganizationForm';
import { RegisterOrganizationForm } from './RegisterOrganizationForm';

type AuthMode = 'login' | 'join' | 'register_org';

export const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<AuthMode>('login');

  // Login form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const safeScrollTop = () => {
    try {
      if (
        typeof window !== 'undefined' &&
        typeof window.scrollTo === 'function' &&
        !window.navigator?.userAgent?.includes('jsdom')
      ) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    } catch {
      // Ignore in non-browser or jsdom test environments
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !password) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const user = await login({ email: cleanEmail, password });
      const dashboardTarget = user.primary_dashboard || 'employee';
      navigate(`/dashboard/${dashboardTarget}`, { replace: true });
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, t('auth.invalidCredentials', 'Incorrect email or password')));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen flex-col bg-surface-50 text-surface-900 transition-colors duration-200 dark:bg-[#090d16] dark:text-white">
      {/* Background Subtle Tactical Grid */}
      <div className="pointer-events-none absolute inset-0 noc-grid-bg opacity-50 dark:opacity-25" />

      {/* Top Command Bar */}
      <header className="relative z-10 flex items-center justify-between border-b border-surface-200 bg-white/80 px-6 py-3.5 backdrop-blur-md dark:border-white/10 dark:bg-surface-900/80">
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-brand-600 via-sky-500 to-cyan-400 text-white shadow-md shadow-brand-500/25">
            <Activity className="h-5 w-5" />
            <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-emerald-400 dark:border-surface-900" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold tracking-tight text-surface-900 dark:text-white">
                {t('app.title', 'ServicePulse')}
              </h1>
              <span className="rounded bg-brand-50 px-1.5 py-0.2 text-[9px] font-bold text-brand-700 ring-1 ring-brand-600/20 dark:bg-brand-950/60 dark:text-brand-300 dark:ring-brand-500/30 font-mono">
                ENTERPRISE NOC
              </span>
            </div>
            <p className="text-[11px] text-surface-500 dark:text-surface-400">
              {t('app.subtitle', 'Hybrid RMM & ITSM Platform')}
            </p>
          </div>
        </div>

        {/* Live Gateway Security Telemetry Center Strip */}
        <div className="hidden md:flex items-center gap-2 font-mono text-[11px]">
          <span className="telemetry-pill">
            <span className="status-dot-online" />
            ZERO-TRUST AUTH GATEWAY
          </span>
          <span className="telemetry-pill">
            SESSION: JTI-ROTATION
          </span>
          <span className="telemetry-pill text-surface-500 dark:text-surface-400">
            ENCRYPTION: ARGON2ID / TLS
          </span>
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <LanguageSwitcher />
        </div>
      </header>

      {/* Main Center Viewport */}
      <main className="relative z-10 flex flex-1 items-center justify-center p-4 sm:p-6 md:p-8 py-8 sm:py-12 overflow-y-auto">
        <div className="w-full max-w-lg space-y-5 my-auto">
          <div className="noc-panel relative overflow-hidden p-6 sm:p-8 shadow-xl shadow-surface-900/5 backdrop-blur-xl dark:border-white/10 dark:shadow-black/40">
            {/* Top Accent Gradient Bar */}
            <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-brand-600 via-sky-400 to-cyan-400" />

            {/* Zero-Trust Telemetry Banner Strip for Auth Gateway */}
            <div className="mb-5 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-surface-200/80 bg-surface-50/80 px-3 py-1.5 text-[11px] font-mono dark:border-white/5 dark:bg-surface-950/60">
              <div className="flex items-center gap-2">
                <span className="status-dot-online" />
                <span className="font-semibold text-surface-700 dark:text-surface-300">ZERO-TRUST GATEWAY</span>
                <span className="text-surface-300 dark:text-surface-700">|</span>
                <span className="text-surface-500 dark:text-surface-400">JTI-ROTATION</span>
              </div>
              <div className="text-surface-400 dark:text-surface-500">
                TLS 1.3 &bull; ARGON2ID
              </div>
            </div>

            {/* Header Titles */}
            <div className="mb-6 text-center">
              <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-600 dark:bg-brand-950/60 dark:text-brand-400">
                <Shield className="h-5 w-5" />
              </div>
              <h2 className="text-xl font-bold tracking-tight text-surface-900 dark:text-white">
                {mode === 'login' && t('auth.loginTitle', 'Sign in to ServicePulse')}
                {mode === 'join' && t('auth.joinTitle', 'Join Existing Organization')}
                {mode === 'register_org' && t('auth.registerOrgTitle', 'Register New Organization')}
              </h2>
              <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">
                {mode === 'login' && t('auth.loginSubtitle', 'Enter your corporate credentials to continue')}
                {mode === 'join' && t('auth.joinSubtitle', 'Use your invitation code to activate your account')}
                {mode === 'register_org' && t('auth.registerOrgSubtitle', 'Apply for a new tenant space for your institution')}
              </p>
            </div>

            {/* Mode Navigation Tabs */}
            <div className="mb-6 flex rounded-xl border border-surface-200 bg-surface-100/80 p-1 text-xs font-semibold dark:border-white/10 dark:bg-surface-800/60">
              <button
                type="button"
                data-testid="tab-login"
                onClick={() => {
                  setMode('login');
                  setError(null);
                  safeScrollTop();
                }}
                className={`flex-1 rounded-lg py-2 transition-all ${
                  mode === 'login'
                    ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
                    : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
                }`}
              >
                {t('auth.tabSignIn', 'Sign In')}
              </button>
              <button
                type="button"
                data-testid="tab-join"
                onClick={() => {
                  setMode('join');
                  setError(null);
                  safeScrollTop();
                }}
                className={`flex-1 rounded-lg py-2 transition-all ${
                  mode === 'join'
                    ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
                    : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
                }`}
              >
                {t('auth.tabJoinOrg', 'Join with Invite')}
              </button>
              <button
                type="button"
                data-testid="tab-register-org"
                onClick={() => {
                  setMode('register_org');
                  setError(null);
                  safeScrollTop();
                }}
                className={`flex-1 rounded-lg py-2 transition-all ${
                  mode === 'register_org'
                    ? 'bg-white text-surface-900 shadow-xs dark:bg-surface-900 dark:text-white'
                    : 'text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white'
                }`}
              >
                {t('auth.tabNewOrg', 'New Organization')}
              </button>
            </div>

            {/* Login Mode */}
            {mode === 'login' && (
              <div>
                {error && (
                  <div className="mb-5 flex items-center gap-2.5 rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
                    <AlertCircle className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleLoginSubmit} className="space-y-4">
                  <div>
                    <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
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
                        placeholder="name@company.com"
                        className="w-full rounded-lg border border-surface-300 bg-white py-2.5 pl-9 pr-3 text-sm font-mono text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-semibold text-surface-700 dark:text-surface-300">
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
                        className="w-full rounded-lg border border-surface-300 bg-white py-2.5 pl-9 pr-10 text-sm font-mono text-surface-900 placeholder:text-surface-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-white/10 dark:bg-surface-800 dark:text-white dark:focus:border-brand-400"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 flex items-center pr-3 text-surface-400 hover:text-surface-600 dark:hover:text-surface-200"
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    data-testid="login-submit-btn"
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-brand-600 to-sky-600 py-2.5 text-sm font-semibold text-white shadow-md shadow-brand-600/20 transition-all hover:from-brand-500 hover:to-sky-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 disabled:opacity-60"
                  >
                    {isSubmitting ? (
                      <span>{t('auth.loggingIn', 'Signing In...')}</span>
                    ) : (
                      <>
                        <span>{t('auth.loginButton', 'Sign In')}</span>
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </form>
              </div>
            )}

            {/* Join Existing Organization Mode */}
            {mode === 'join' && (
              <JoinOrganizationForm onSwitchToLogin={() => setMode('login')} />
            )}

            {/* Register New Organization Mode */}
            {mode === 'register_org' && (
              <RegisterOrganizationForm onSwitchToLogin={() => setMode('login')} />
            )}
          </div>

          <div className="flex items-center justify-center gap-2 text-center text-xs text-surface-500 dark:text-surface-400">
            <Sparkles className="h-3.5 w-3.5 text-brand-500" />
            <span>{t('app.tagline', 'Enterprise Hybrid RMM & ITSM Platform')} &bull; &copy; {new Date().getFullYear()} ServicePulse Technologies</span>
          </div>
        </div>
      </main>
    </div>
  );
};
