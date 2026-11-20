import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { Seo } from '@/shared/seo/Seo';
import { Page } from '@/shared/ui/Page';
import { GuestHome, SessionCheckingHome, UserHome } from '@/widgets/home';

export function HomePage() {
  const { t } = useI18n();
  const { role, profile, status } = useAuth();
  const checking = status === 'checking';

  return (
    <>
      <Seo path="/" />
      {role === 'guest' && !checking ? (
        <GuestHome />
      ) : (
        <Page title={t(checking ? 'home.title' : 'nav.home')} eyebrow={t('nav.groupOverview')} seo={false}>
          {checking ? <SessionCheckingHome /> : <UserHome isAdmin={role === 'admin'} profile={profile} />}
        </Page>
      )}
    </>
  );
}
