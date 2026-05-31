import { Link } from 'react-router-dom';
import { useAuth } from '@/features/auth/use-auth';
import { GuestHome, SessionCheckingHome, UserHome } from '@/features/home/components/HomePanels';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { Page } from '@/shared/ui/Page';

export function HomePage() {
  const { t } = useI18n();
  const { role, profile, status } = useAuth();

  if (status === 'checking') {
    return (
      <Page title={t('home.title')} description={t('auth.checking')}>
        <SessionCheckingHome />
      </Page>
    );
  }

  if (role === 'guest') {
    return <GuestHome />;
  }

  return (
    <Page
      title={role === 'admin' ? t('home.adminTitle') : t('home.userTitle')}
      eyebrow={profile?.nickname ?? t(`auth.${role}`)}
      description={role === 'admin' ? t('home.adminBody') : 'Your workspace skeleton is ready for library and feed modules.'}
      actions={
        <Link className="button button-primary" to={routes.search}>
          Explore catalog
        </Link>
      }
    >
      <UserHome isAdmin={role === 'admin'} profile={profile} />
    </Page>
  );
}
