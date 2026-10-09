import { useAuth } from '@/entities/session';
import { GuestHome, SessionCheckingHome, UserHome } from '@/widgets/home';
import { useI18n } from '@/shared/i18n';
import { Seo } from '@/shared/seo/Seo';
import { Page } from '@/shared/ui/Page';

export function HomePage() {
  const { t } = useI18n();
  const { role, profile, status } = useAuth();

  if (status === 'checking') {
    return (
      <Page title={t('home.title')} eyebrow={t('nav.groupOverview')} seo={false}>
        <Seo
          title="Noshiro DB"
          description="Explore anime and galgames, browse weekly anime, and keep track of marks, reviews, and collections."
          path="/"
        />
        <SessionCheckingHome />
      </Page>
    );
  }

  if (role === 'guest') {
    return (
      <>
        <Seo
          title="Noshiro DB"
          description="Explore anime and galgames, browse weekly anime, and keep track of marks, reviews, and collections."
          path="/"
        />
        <GuestHome />
      </>
    );
  }

  return (
    <Page title={t('nav.home')} eyebrow={t('nav.groupOverview')} seo={false}>
      <Seo
        title="Noshiro DB"
        description="Explore anime and galgames, browse weekly anime, and keep track of marks, reviews, and collections."
        path="/"
      />
      <UserHome isAdmin={role === 'admin'} profile={profile} />
    </Page>
  );
}
