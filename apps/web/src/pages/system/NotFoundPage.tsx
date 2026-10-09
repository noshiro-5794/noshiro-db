import { Link, useLocation, useNavigate, useRouter } from '@tanstack/react-router';
import { ArrowLeft, Home, Search } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Seo } from '@/shared/seo/Seo';
import { Button } from '@/shared/ui/Button';

export function NotFoundPage() {
  const navigate = useNavigate();
  const router = useRouter();
  const location = useLocation();
  const { t } = useI18n();

  function handleBack() {
    if (location.state.__TSR_index === 0) {
      void navigate({ replace: true, to: '/' });
      return;
    }
    router.history.back();
  }

  return (
    <section className="grid min-h-full place-items-center px-5 py-16">
      <Seo noindex title={t('notFound.title')} description={t('notFound.description')} />
      <div className="mx-auto grid w-full max-w-xl justify-items-center text-center">
        <span className="rounded-full border border-[var(--ui-border)] px-3 py-1 text-xs font-semibold uppercase tracking-normal text-[var(--ui-text-muted)]">
          404
        </span>
        <h1 className="mt-5 text-4xl font-semibold tracking-normal text-[var(--ui-text)] sm:text-5xl">
          {t('notFound.title')}
        </h1>
        <p className="mt-4 max-w-md text-sm leading-6 text-[var(--ui-text-muted)]">{t('notFound.description')}</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button type="button" variant="secondary" onClick={handleBack}>
            <ArrowLeft className="size-4" />
            {t('notFound.back')}
          </Button>
          <Button asChild>
            <Link to={routes.home}>
              <Home className="size-4" />
              {t('notFound.action')}
            </Link>
          </Button>
          <Button asChild variant="ghost">
            <Link to={routes.search}>
              <Search className="size-4" />
              {t('nav.search')}
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
