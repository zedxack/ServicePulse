import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LanguageSwitcher } from '../shared/components/LanguageSwitcher';
import '../i18n/config';
import i18n from 'i18next';

describe('LanguageSwitcher Component & i18n Localization', () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage('uz');
  });

  it('renders with default language uz', () => {
    render(<LanguageSwitcher />);
    const select = screen.getByLabelText('Language selector') as HTMLSelectElement;
    expect(select.value).toBe('uz');
  });

  it('changes active language to ru and en upon selection', async () => {
    render(<LanguageSwitcher />);
    const select = screen.getByLabelText('Language selector') as HTMLSelectElement;

    // Switch to Russian
    fireEvent.change(select, { target: { value: 'ru' } });
    expect(i18n.language).toContain('ru');
    expect(localStorage.getItem('i18nextLng')).toBe('ru');

    // Switch to English
    fireEvent.change(select, { target: { value: 'en' } });
    expect(i18n.language).toContain('en');
    expect(localStorage.getItem('i18nextLng')).toBe('en');
  });
});
