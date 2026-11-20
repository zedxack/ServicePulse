import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  X,
  Terminal,
  Copy,
  Check,
  ShieldCheck,
  Server,
  AlertCircle,
  RefreshCw,
  Info,
} from 'lucide-react';
import { inventoryApi } from '../../shared/api/inventory';
import { AgentBootstrapConfigResponse } from '../../shared/types/inventory';
import { Badge } from '../../shared/components/Badge';

interface AgentBootstrapModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AgentBootstrapModal: React.FC<AgentBootstrapModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { t } = useTranslation();
  const [platform, setPlatform] = useState<'windows' | 'linux'>('windows');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<AgentBootstrapConfigResponse | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchConfig();
    }
  }, [isOpen]);

  const fetchConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await inventoryApi.getAgentBootstrapConfig();
      setConfig(data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || t('inventory.bootstrapFetchFailed', 'Failed to load agent bootstrap configuration.');
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  const currentCommand = platform === 'windows'
    ? config?.powershell_command || ''
    : config?.linux_bash_command || '';

  const handleCopy = async () => {
    if (!currentCommand) return;
    try {
      await navigator.clipboard.writeText(currentCommand);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (e) {
      console.error('Failed to copy command to clipboard', e);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="agent-bootstrap-title"
    >
      <div className="relative w-full max-w-3xl bg-[var(--color-bg-primary)] border border-[var(--color-border-subtle)] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)]/50">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h2 id="agent-bootstrap-title" className="text-lg font-semibold text-[var(--color-text-primary)]">
                {t('inventory.deployAgent', '1-Click Agent Bootstrap Deployer')}
              </h2>
              <p className="text-xs text-[var(--color-text-secondary)]">
                {t('inventory.deployAgentDesc', 'Enroll nodes into ServicePulse RMM Fleet in seconds with zero manual configuration')}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="flex items-start space-x-3 p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="font-medium">{t('common.error', 'Error')}:</span> {error}
              </div>
              <button
                onClick={fetchConfig}
                className="text-xs underline hover:no-underline font-medium text-rose-300"
              >
                {t('common.retry', 'Retry')}
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-3">
              <RefreshCw className="w-8 h-8 text-primary-500 animate-spin" />
              <p className="text-sm text-[var(--color-text-secondary)]">
                {t('inventory.loadingBootstrap', 'Generating secure agent bootstrap configuration...')}
              </p>
            </div>
          ) : config ? (
            <>
              {/* Target Fleet Overview Card */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border-subtle)]">
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                    {t('inventory.serverEndpoint', 'Server Endpoint')}
                  </div>
                  <div className="text-xs font-mono text-[var(--color-text-primary)] truncate font-medium">
                    {config.server_url}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                    {t('inventory.organization', 'Organization')}
                  </div>
                  <div className="text-xs font-medium text-[var(--color-text-primary)] truncate">
                    {config.organization_name} <span className="text-[10px] text-[var(--color-text-secondary)] font-mono">(ID: {config.organization_id})</span>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--color-text-secondary)] mb-1">
                    {t('inventory.agentVersion', 'Agent Version / Token')}
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant="online">v{config.agent_version}</Badge>
                    <span className="text-xs font-mono text-emerald-400 font-medium">Enrolled Secret ✓</span>
                  </div>
                </div>
              </div>

              {/* OS Platform Selector */}
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] mb-2">
                  {t('inventory.selectPlatform', 'Select Target Operating System')}
                </label>
                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={() => setPlatform('windows')}
                    className={`flex-1 flex items-center justify-center space-x-2.5 py-2.5 px-4 rounded-lg border text-sm font-medium transition-all ${
                      platform === 'windows'
                        ? 'bg-primary-500/10 border-primary-500 text-primary-400 shadow-sm'
                        : 'bg-[var(--color-bg-secondary)] border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-default)]'
                    }`}
                  >
                    <Server className="w-4 h-4" />
                    <span>Windows PowerShell (Admin)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPlatform('linux')}
                    className={`flex-1 flex items-center justify-center space-x-2.5 py-2.5 px-4 rounded-lg border text-sm font-medium transition-all ${
                      platform === 'linux'
                        ? 'bg-primary-500/10 border-primary-500 text-primary-400 shadow-sm'
                        : 'bg-[var(--color-bg-secondary)] border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-default)]'
                    }`}
                  >
                    <Terminal className="w-4 h-4" />
                    <span>Linux / macOS (Bash / sudo)</span>
                  </button>
                </div>
              </div>

              {/* One-Liner Command Box */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono uppercase tracking-wider text-[var(--color-text-secondary)]">
                    {platform === 'windows' ? 'PowerShell 1-Click Bootstrap' : 'Linux / Bash 1-Click Bootstrap'}
                  </span>
                  <button
                    type="button"
                    onClick={handleCopy}
                    className={`flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium transition-all ${
                      copied
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)] border border-[var(--color-border-subtle)]'
                    }`}
                    data-testid="copy-bootstrap-btn"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span>{t('common.copied', 'Copied!')}</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>{t('inventory.copyCommand', 'Copy Command')}</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="relative group">
                  <pre
                    className="p-4 rounded-lg bg-[#0d1117] text-[#58a6ff] border border-gray-800 font-mono text-xs overflow-x-auto whitespace-pre-wrap break-all leading-relaxed select-all"
                    data-testid="bootstrap-command-text"
                  >
                    {currentCommand}
                  </pre>
                </div>
              </div>

              {/* Step-by-Step Instructions */}
              <div className="p-4 rounded-lg bg-[var(--color-bg-secondary)]/60 border border-[var(--color-border-subtle)] space-y-2">
                <div className="flex items-center space-x-2 text-xs font-semibold text-[var(--color-text-primary)]">
                  <Info className="w-4 h-4 text-primary-400" />
                  <span>{t('inventory.deploymentSteps', 'Deployment Instructions')}:</span>
                </div>
                <ol className="text-xs text-[var(--color-text-secondary)] space-y-1.5 list-decimal list-inside pl-1">
                  {config.manual_steps.map((step, idx) => (
                    <li key={idx} className="leading-normal">
                      {step}
                    </li>
                  ))}
                  <li className="leading-normal">
                    {t('inventory.nodeAutoCheckin', 'The node will immediately handshake with ServicePulse, report system telemetry, and appear in the Inventory Explorer.')}
                  </li>
                </ol>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-secondary)]/50">
          <div className="flex items-center space-x-2 text-xs text-[var(--color-text-secondary)]">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>{t('inventory.encryptedEnrollment', 'TLS 1.3 End-to-End Encrypted Node Enrollment')}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] border border-[var(--color-border-subtle)] text-xs font-medium text-[var(--color-text-primary)] transition-colors"
          >
            {t('common.close', 'Close')}
          </button>
        </div>
      </div>
    </div>
  );
};
