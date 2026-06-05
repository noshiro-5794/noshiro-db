import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Home, Search } from 'lucide-react';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { Button } from '@/shared/ui/Button';

export function NotFoundPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useI18n();

  function handleBack() {
    if (location.key === 'default') {
      navigate(routes.home, { replace: true });
      return;
    }
    navigate(-1);
  }

  return (
    <section className="grid min-h-full place-items-center px-5 py-16">
      <div className="mx-auto grid w-full max-w-xl justify-items-center text-center">
        <span className="rounded-full border border-neutral-200 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:border-neutral-800 dark:text-neutral-400">
          404
        </span>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight text-neutral-950 dark:text-white sm:text-5xl">
          {t('notFound.title')}
        </h1>
        <p className="mt-4 max-w-md text-sm leading-6 text-neutral-500 dark:text-neutral-400">
          {t('notFound.description')}
        </p>
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
