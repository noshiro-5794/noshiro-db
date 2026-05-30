import { AuthEntry } from '@/features/auth/AuthEntry';
import { useAuth } from '@/features/auth/use-auth';
import { useI18n } from '@/features/i18n/use-i18n';
import { Page } from '@/shared/ui/Page';

export function HomePage() {
  const { t } = useI18n();
  const { role, profile, status } = useAuth();

  if (status === 'checking') {
    return (
      <Page title={t('home.title')}>
        <p>{t('auth.checking')}</p>
      </Page>
    );
  }

  if (role === 'guest') {
    return (
      <Page title={t('home.title')}>
        <AuthEntry />
      </Page>
    );
  }

  return (
    <Page title={role === 'admin' ? t('home.adminTitle') : t('home.userTitle')}>
      <p>{profile?.nickname}</p>
      {role === 'admin' ? <p>{t('home.adminBody')}</p> : null}
    </Page>
  );
}
