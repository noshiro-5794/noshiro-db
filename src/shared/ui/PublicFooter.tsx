import { Link } from 'react-router-dom';
import { useAuth } from '@/features/auth/use-auth';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';

export function PublicFooter() {
  const { t } = useI18n();
  const auth = useAuth();

  return (
    <footer className="border-t border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
      <div className="mx-auto flex max-w-6xl flex-col gap-5 px-5 py-8 text-sm text-neutral-500 dark:text-neutral-400 md:flex-row md:items-center md:justify-between">
        <div>
          <Link className="font-semibold text-neutral-950 transition hover:text-[var(--color-accent-strong)] dark:text-white" to={routes.home}>
            Noshiro DB
          </Link>
          <p className="mt-1">© 2026 Noshiro DB. All rights reserved.</p>
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          <Link className="transition hover:text-neutral-950 dark:hover:text-white" to={routes.docsIntroduction}>
            {t('nav.docs')}
          </Link>
          <Link className="transition hover:text-neutral-950 dark:hover:text-white" to={routes.search}>
            {t('nav.search')}
          </Link>
          <Link className="transition hover:text-neutral-950 dark:hover:text-white" to={routes.calendar}>
            {t('nav.calendar')}
          </Link>
          <a
            className="transition hover:text-neutral-950 dark:hover:text-white"
            href="https://github.com/LHYHENRY/noshiro-db-frontend"
            rel="noreferrer"
            target="_blank"
          >
            GitHub
          </a>
          {auth.isAuthenticated ? (
            <Link className="transition hover:text-neutral-950 dark:hover:text-white" to={routes.me}>
              {t('nav.me')}
            </Link>
          ) : (
            <Link className="transition hover:text-neutral-950 dark:hover:text-white" to={routes.login}>
              {t('auth.login')}
            </Link>
          )}
        </div>
      </div>
    </footer>
  );
}
