import { useState } from 'react';
import { Navigate, useNavigate } from '@tanstack/react-router';
import { useAuth } from '@/entities/session';
import { ProfileAvatarPanel } from '@/features/profile-avatar';
import { PreferenceSettingsForm, ProfileSettingsForm } from '@/features/profile-settings';
import { type MessageKey, useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { EmptyState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { toast } from '@/shared/ui/toast';
import { PublicFooter } from '@/widgets/public-footer';

export function SettingsPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const { t } = useI18n();
  const [noticeMessageKey, setNoticeMessageKey] = useState<MessageKey | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const profile = auth.profile;

  function showNotice(messageKey: MessageKey) {
    setErrorMessage('');
    setNoticeMessageKey(messageKey);
  }

  function showError(message: string) {
    setNoticeMessageKey(null);
    setErrorMessage(message);
  }

  async function signOut() {
    try {
      await auth.logout();
    } catch {
      toast.error(t('common.requestFailed'));
    } finally {
      await navigate({ replace: true, to: '/' });
    }
  }

  if (auth.status === 'checking') {
    return (
      <Page title={t('settings.title')} eyebrow={t('nav.groupMore')}>
        <LoadingState title={t('auth.checking')} />
      </Page>
    );
  }

  if (auth.role === 'guest') return <Navigate replace to={routes.login} />;

  if (!profile) {
    return (
      <Page title={t('settings.title')} eyebrow={t('nav.groupMore')}>
        <EmptyState title={t('settings.profileUnavailableTitle')} description={t('settings.profileUnavailableBody')} />
      </Page>
    );
  }

  const formProps = {
    profile,
    patchProfile: auth.patchProfile,
    onError: showError,
    onNotice: showNotice,
  };

  return (
    <Page title={t('settings.title')} eyebrow={t('nav.groupMore')}>
      <div className="grid gap-8 lg:grid-cols-[280px_minmax(0,1fr)]">
        <ProfileAvatarPanel {...formProps} sessionBusy={auth.loading} onSignOut={signOut} />
        <div className="grid content-start gap-5">
          <ProfileSettingsForm {...formProps} />
          <PreferenceSettingsForm {...formProps} />
          {noticeMessageKey ? (
            <p className="rounded-lg bg-[var(--ui-success-soft)] px-3 py-2 text-sm text-[var(--ui-success-text)]">
              {t(noticeMessageKey)}
            </p>
          ) : null}
          {errorMessage ? (
            <p className="rounded-lg bg-[var(--ui-danger-soft)] px-3 py-2 text-sm text-[var(--ui-danger-text)]">
              {errorMessage}
            </p>
          ) : null}
          <PublicFooter variant="compact" />
        </div>
      </div>
    </Page>
  );
}
