import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { CalendarBoard } from '@/features/calendar/components/CalendarBoard';
import { SearchShowcase } from '@/features/home/components/SearchShowcase';
import { socialQueries } from '@/features/social/social-queries';
import { subjectQueries } from '@/features/subjects/subject-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import type { CurrentUserProfile } from '@/lib/api/types';
import { routes } from '@/routes/paths';

export function SessionCheckingHome() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="h-44 rounded-xl border border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900 sm:col-span-2" />
      <div className="h-44 rounded-xl border border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900" />
    </div>
  );
}

export function GuestHome() {
  const { t } = useI18n();
  const calendarQuery = useQuery(subjectQueries.calendar());

  return (
    <div className="space-y-14 pb-10">
      <section className="mx-auto flex min-h-[calc(100svh-23rem)] max-w-5xl flex-col items-center justify-center px-4 py-10 text-center sm:py-12">
        <Link
          className="motion-rise inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs font-medium text-neutral-600 shadow-sm transition hover:border-[var(--color-accent-border)] hover:text-[var(--color-accent-strong)] dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-400"
          to={routes.docsIntroduction}
        >
          <span>{t('public.announcement')}</span>
          <span className="text-neutral-400">/</span>
          <span>{t('public.announcementAction')}</span>
        </Link>
        <h1 className="motion-rise motion-delay-1 mt-4 max-w-4xl text-4xl font-semibold tracking-tight text-neutral-950 dark:text-white sm:text-6xl">
          {t('public.tagline')}
        </h1>
        <p className="motion-rise motion-delay-2 mt-4 max-w-2xl text-base leading-7 text-neutral-500 dark:text-neutral-400 sm:text-lg">
          {t('public.heroBody')}
        </p>
        <div className="motion-rise motion-delay-3 mt-6 flex flex-wrap justify-center gap-3">
          <Link className="button button-primary h-10 rounded-full px-5" to={routes.register}>
            {t('auth.register')}
          </Link>
          <Link className="button button-secondary h-10 rounded-full px-5" to={routes.search}>
            {t('public.searchAction')}
          </Link>
        </div>
      </section>

      <section className="motion-rise motion-delay-4 mx-auto max-w-6xl px-4">
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">
              {t('calendar.title')}
            </h2>
            <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">{t('public.calendarBody')}</p>
          </div>
          <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.calendar}>
            {t('public.more')}
          </Link>
        </div>
        <CalendarBoard groups={calendarQuery.data} isLoading={calendarQuery.isLoading} />
      </section>

      <div className="motion-rise motion-delay-4">
        <SearchShowcase />
      </div>
    </div>
  );
}

type UserHomeProps = {
  isAdmin: boolean;
  profile: CurrentUserProfile | null;
};

export function UserHome({ isAdmin, profile }: UserHomeProps) {
  const activityQuery = useQuery(socialQueries.feed({ page_size: 8, ordering: '-created_at' }));
  const activities = activityQuery.data?.results ?? [];

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-950">
        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="text-xs font-semibold uppercase text-[var(--color-accent-strong)]">Activity</span>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-neutral-950 dark:text-white">Recent behavior</h2>
          </div>
        </div>

        <div className="mt-5 grid gap-3">
          {activities.length > 0 ? (
            activities.map((activity) => (
              <article className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800" key={activity.id}>
                <p className="text-sm font-semibold text-neutral-950 dark:text-white">
                  {activity.subject?.display_title || activity.subject?.title || activity.review?.title || activity.collection?.name || activity.activity_type}
                </p>
                <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{activity.activity_type}</p>
              </article>
            ))
          ) : (
            <div className="rounded-xl border border-dashed border-neutral-200 p-8 text-center text-sm text-neutral-500 dark:border-neutral-800 dark:text-neutral-400">
              Your activity feed will appear here after you mark subjects, write reviews, or follow users.
            </div>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-950">
        <span className="text-xs font-semibold uppercase text-[var(--color-accent-strong)]">Account</span>
        <div className="mt-4 flex items-center gap-3">
          <img className="size-12 rounded-xl bg-neutral-100 object-cover dark:bg-neutral-900" src={profile?.avatar || '/assets/placeholders/avatar.png'} alt="" />
          <div className="min-w-0">
            <h2 className="truncate font-semibold text-neutral-950 dark:text-white">{profile?.nickname}</h2>
            <p className="truncate text-sm text-neutral-500 dark:text-neutral-400">{profile?.email}</p>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-3 gap-3">
          <div>
            <strong className="text-2xl text-neutral-950 dark:text-white">0</strong>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Watching</p>
          </div>
          <div>
            <strong className="text-2xl text-neutral-950 dark:text-white">0</strong>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Done</p>
          </div>
          <div>
            <strong className="text-2xl text-neutral-950 dark:text-white">0</strong>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Reviews</p>
          </div>
        </div>
      </section>
      {isAdmin ? (
        <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-950 lg:col-span-2">
          <span className="text-xs font-semibold uppercase text-[var(--color-accent-strong)]">Admin</span>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-neutral-950 dark:text-white">Sync controls</h2>
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">Admin-only operation panels will be connected after the page skeleton.</p>
        </section>
      ) : null}
    </div>
  );
}
