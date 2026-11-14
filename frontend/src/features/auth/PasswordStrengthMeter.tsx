import React from 'react';
import { useTranslation } from 'react-i18next';
import { Check, X } from 'lucide-react';

interface PasswordStrengthProps {
  password: string;
}

export interface PasswordScore {
  score: number; // 0 to 4
  hasLength: boolean;
  hasUpper: boolean;
  hasLower: boolean;
  hasDigit: boolean;
  hasSpecial: boolean;
}

export const evaluatePassword = (password: string): PasswordScore => {
  const hasLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>\-_=+[\]\\/`~]/.test(password);

  let score = 0;
  if (hasLength) score += 1;
  if (hasUpper && hasLower) score += 1;
  if (hasDigit) score += 1;
  if (hasSpecial) score += 1;

  return { score, hasLength, hasUpper, hasLower, hasDigit, hasSpecial };
};

export const PasswordStrengthMeter: React.FC<PasswordStrengthProps> = ({ password }) => {
  const { t } = useTranslation();
  if (!password) return null;

  const { score, hasLength, hasUpper, hasLower, hasDigit, hasSpecial } = evaluatePassword(password);

  const getLabel = () => {
    switch (score) {
      case 0:
      case 1:
        return { label: t('auth.strengthWeak', 'Weak'), color: 'bg-red-500', text: 'text-red-600' };
      case 2:
        return { label: t('auth.strengthFair', 'Fair'), color: 'bg-amber-500', text: 'text-amber-600' };
      case 3:
        return { label: t('auth.strengthGood', 'Good'), color: 'bg-blue-500', text: 'text-blue-600' };
      case 4:
        return { label: t('auth.strengthStrong', 'Strong'), color: 'bg-emerald-500', text: 'text-emerald-600' };
      default:
        return { label: '', color: 'bg-surface-200', text: 'text-surface-500' };
    }
  };

  const { label, color, text } = getLabel();

  return (
    <div className="mt-2 space-y-2">
      {/* Progress Bars */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-surface-500">{t('auth.passwordStrength', 'Password strength')}:</span>
        <span className={`font-semibold ${text}`}>{label}</span>
      </div>
      <div className="grid grid-cols-4 gap-1.5">
        {[1, 2, 3, 4].map((step) => (
          <div
            key={step}
            className={`h-1.5 rounded-full transition-colors duration-200 ${
              score >= step ? color : 'bg-surface-200'
            }`}
          />
        ))}
      </div>

      {/* Criteria Checklist */}
      <div className="grid grid-cols-2 gap-1.5 pt-1 text-[11px] text-surface-500">
        <div className="flex items-center gap-1">
          {hasLength ? <Check className="h-3 w-3 text-emerald-600" /> : <X className="h-3 w-3 text-surface-400" />}
          <span>{t('auth.ruleLength', '8+ characters')}</span>
        </div>
        <div className="flex items-center gap-1">
          {hasUpper && hasLower ? <Check className="h-3 w-3 text-emerald-600" /> : <X className="h-3 w-3 text-surface-400" />}
          <span>{t('auth.ruleCase', 'Upper & lowercase')}</span>
        </div>
        <div className="flex items-center gap-1">
          {hasDigit ? <Check className="h-3 w-3 text-emerald-600" /> : <X className="h-3 w-3 text-surface-400" />}
          <span>{t('auth.ruleDigit', 'At least 1 number')}</span>
        </div>
        <div className="flex items-center gap-1">
          {hasSpecial ? <Check className="h-3 w-3 text-emerald-600" /> : <X className="h-3 w-3 text-surface-400" />}
          <span>{t('auth.ruleSpecial', 'Special character')}</span>
        </div>
      </div>
    </div>
  );
};
