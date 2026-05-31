import { Navigate } from 'react-router-dom';
import { useI18n } from '@/features/i18n/use-i18n';
import { useAuth } from '@/features/auth/use-auth';
import { ProfileOverview } from '@/features/profile/components/ProfileOverview';
import { Page } from '@/shared/ui/Page';
import { routes } from '@/routes/paths';
import { LoadingState } from '@/shared/ui/FeedbackState';

export function MePage() {
  const { t } = useI18n();
  const auth = useAuth();
  const { role, profile } = auth;

  if (auth.status === 'checking') {
    return (
      <Page title={t('me.title')} description={t('auth.checking')}>
        <LoadingState title={t('auth.checking')} />
      </Page>
    );
  }

  if (role === 'guest') {
    return <Navigate replace to={routes.login} />;
  }

  return (
    <Page
      title={t('me.title')}
      eyebrow={profile?.nickname ?? t(`auth.${role}`)}
      description={profile?.bio || t('me.description')}
    >
      <ProfileOverview auth={auth} profile={profile} />
    </Page>
  );
}
