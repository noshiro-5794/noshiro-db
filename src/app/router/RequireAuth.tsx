import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { useLocation, useRouter } from '@tanstack/react-router';
import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { returnTargetFromState } from '@/shared/routing/route-state';
import { LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

export function RequireAuth({ adminOnly = false, children }: { adminOnly?: boolean; children: ReactNode }) {
  const auth = useAuth();
  const { t } = useI18n();
  const location = useLocation();
  const router = useRouter();
  const redirectTo =
    auth.status !== 'checking' && !auth.isAuthenticated
      ? routes.login
      : adminOnly && auth.status !== 'checking' && auth.role !== 'admin'
        ? routes.home
        : null;
  const loginReturnTo =
    location.pathname === routes.login ? returnTargetFromState(location.state, routes.home) : location.href;

  useEffect(() => {
    if (!redirectTo) return;

    void router.navigate({
      replace: true,
      ...(redirectTo === routes.login ? { state: { returnTo: loginReturnTo } } : {}),
      to: redirectTo,
    });
  }, [loginReturnTo, redirectTo, router]);

  if (auth.status === 'checking') {
    return (
      <Page title="Noshiro DB">
        <LoadingState title={t('auth.checking')} />
      </Page>
    );
  }

  if (redirectTo) {
    return (
      <Page title="Noshiro DB">
        <LoadingState title={t('auth.checking')} />
      </Page>
    );
  }

  return children;
}
