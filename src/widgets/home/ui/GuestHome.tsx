import { Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Search, UserPlus } from 'lucide-react';
import { subjectQueries } from '@/entities/subject';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import '@/shared/ui/motion.css';
import { CalendarBoard } from './CalendarBoard';
import { SearchShowcase } from './SearchShowcase';

export function GuestHome() {
  const { t } = useI18n();
  const calendarQuery = useQuery(subjectQueries.calendar());

  return (
    <div className="space-y-10 pb-10">
      <section className="mx-auto flex min-h-[390px] max-w-5xl flex-col items-center justify-center px-4 py-10 text-center sm:min-h-[440px]">
        <Link
          className="motion-rise inline-flex items-center gap-2 rounded-[var(--ui-radius-control)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] px-2.5 py-1 text-xs font-medium text-[var(--ui-text-muted)] transition hover:border-[var(--ui-accent-border)] hover:bg-[var(--ui-bg-subtle)] hover:text-[var(--ui-accent-text)]"
          params={{ slug: 'introduction' }}
          to="/docs/$slug"
        >
          <span>{t('public.announcement')}</span>
          <span className="text-[var(--ui-text-subtle)]">/</span>
          <span>{t('public.announcementAction')}</span>
        </Link>
        <h1 className="motion-rise motion-delay-1 mt-5 max-w-4xl text-4xl font-semibold text-[var(--ui-text)] sm:text-5xl">
          {t('public.tagline')}
        </h1>
        <p className="motion-rise motion-delay-2 mt-4 max-w-2xl text-[15px] leading-7 text-[var(--ui-text-muted)] sm:text-base">
          {t('public.heroBody')}
        </p>
        <div className="motion-rise motion-delay-3 mt-6 flex flex-wrap justify-center gap-3">
          <Button asChild size="lg">
            <Link to={routes.search}>
              <Search className="size-4" /> {t('public.searchAction')}
            </Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link to={routes.register}>
              <UserPlus className="size-4" /> {t('auth.register')}
            </Link>
          </Button>
        </div>
      </section>

      <section className="motion-rise motion-delay-4 mx-auto max-w-6xl px-4">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[var(--ui-text)]">{t('calendar.title')}</h2>
            <p className="mt-1 text-[13px] text-[var(--ui-text-muted)]">{t('public.calendarBody')}</p>
          </div>
          <Link className="text-[13px] font-medium text-[var(--ui-accent-text)]" to={routes.calendar}>
            {t('public.more')}
          </Link>
        </div>
        <CalendarBoard
          groups={calendarQuery.data}
          isError={calendarQuery.isError}
          isLoading={calendarQuery.isLoading}
        />
      </section>

      <div className="motion-rise motion-delay-4">
        <SearchShowcase />
      </div>
    </div>
  );
}

export function SessionCheckingHome() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="h-44 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)] sm:col-span-2" />
      <div className="h-44 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)]" />
    </div>
  );
}
