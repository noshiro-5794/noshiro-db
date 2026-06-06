import { useAuth } from '@/features/auth/use-auth';
import { GuestHome, SessionCheckingHome, UserHome } from '@/features/home/components/HomePanels';
import { useI18n } from '@/features/i18n/use-i18n';
import { Seo } from '@/shared/seo/Seo';
import { Page } from '@/shared/ui/Page';

export function HomePage() {
  const { t } = useI18n();
  const { role, profile, status } = useAuth();

  if (status === 'checking') {
    return (
      <Page title={t('home.title')} eyebrow={t('nav.groupOverview')} seo={false}>
        <Seo title="Noshiro DB" description="Explore anime and galgames, browse weekly anime, and keep track of marks, reviews, and collections." path="/" />
        <SessionCheckingHome />
      </Page>
    );
  }

  if (role === 'guest') {
    return (
      <>
        <Seo title="Noshiro DB" description="Explore anime and galgames, browse weekly anime, and keep track of marks, reviews, and collections." path="/" />
        <GuestHome />
      </>
    );
  }

  return (
    <Page title={role === 'admin' ? t('home.adminTitle') : t('nav.home')} eyebrow={t('nav.groupOverview')} seo={false}>
      <Seo title="Noshiro DB" description="Explore anime and galgames, browse weekly anime, and keep track of marks, reviews, and collections." path="/" />
      <UserHome isAdmin={role === 'admin'} profile={profile} />
    </Page>
  );
}
