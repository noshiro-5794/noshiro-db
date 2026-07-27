import { useMemo } from 'react';
import { Link, Navigate, useSearchParams } from '@/shared/routing/navigation';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { CalendarDays, ExternalLink, FileText, Layers3, Library, Settings, Users } from 'lucide-react';
import { profileApi } from '@/entities/session';
import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { libraryQueries } from '@/entities/library';
import { communityActivitiesApi } from '@/entities/community';
import { communityQueryKeys } from '@/entities/community';
import { publicUserQueries } from '@/entities/user';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { EmptyState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

const avatarPlaceholder = '/assets/placeholders/avatar.png';
const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const activityPageSize = 8;
const monthLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function getNextPage(lastPage: { next: string | null }, pages: unknown[]) {
  return lastPage.next ? pages.length + 1 : undefined;
}

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function getBrowserTimeZone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
}

function toLocalDateKey(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function buildYearDays(year: number) {
  const days: string[] = [];
  const cursor = new Date(Date.UTC(year, 0, 1));
  const end = new Date(Date.UTC(year + 1, 0, 1));
  while (cursor < end) {
    days.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return days;
}

function getWeekIndex(date: string) {
  const day = new Date(`${date}T00:00:00Z`);
  const start = new Date(Date.UTC(day.getUTCFullYear(), 0, 1));
  const offset = start.getUTCDay();
  return Math.floor((offset + Math.floor((day.getTime() - start.getTime()) / 86400000)) / 7);
}

function heatClass(count: number) {
  if (count <= 0) return 'bg-[var(--color-surface-muted)] text-transparent';
  if (count === 1) return 'bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]';
  if (count <= 3) return 'bg-[var(--color-accent)] text-white opacity-60';
  if (count <= 6) return 'bg-[var(--color-accent)] text-white opacity-80';
  return 'bg-[var(--color-accent)] text-[var(--color-accent-contrast)]';
}

function activityTitle(activity: {
  activity_type: string;
  subject?: {
    display_title?: string;
    title?: string;
    display_subtitle?: string;
    image_thumbnail?: string | null;
    image?: string | null;
  } | null;
  review?: { title: string } | null;
  collection?: { name: string } | null;
}) {
  return (
    activity.subject?.display_title ||
    activity.subject?.title ||
    activity.review?.title ||
    activity.collection?.name ||
    activity.activity_type.replaceAll('_', ' ')
  );
}

export function MePage() {
  const auth = useAuth();
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentYear = new Date().getFullYear();
  const selectedYear = Number(searchParams.get('year') ?? currentYear) || currentYear;
  const profile = auth.profile;
  const publicUserId = Number(profile?.user_id ?? 0);
  const browserTimeZone = useMemo(() => getBrowserTimeZone(), []);

  const statsQuery = useQuery({
    queryKey: ['profile', 'stats', selectedYear, browserTimeZone],
    queryFn: () => profileApi.getStats({ year: selectedYear, timezone: browserTimeZone }),
    enabled: auth.isAuthenticated,
  });
  const subjectsQuery = useQuery({
    ...libraryQueries.userSubjects({ page_size: 500, ordering: '-created_at' }),
    enabled: auth.isAuthenticated,
  });
  const collectionsQuery = useQuery({
    ...libraryQueries.collections({ page_size: 1 }),
    enabled: auth.isAuthenticated,
  });
  const activityQuery = useInfiniteQuery({
    queryKey: [
      ...communityQueryKeys.myActivities({ page_size: activityPageSize, ordering: '-created_at' }),
      'stream',
    ] as const,
    queryFn: ({ pageParam }) =>
      communityActivitiesApi.listMine({ page: pageParam, page_size: activityPageSize, ordering: '-created_at' }),
    initialPageParam: 1,
    getNextPageParam: getNextPage,
    enabled: auth.isAuthenticated,
  });
  const reviewsQuery = useQuery({
    ...libraryQueries.reviews({ page_size: 3, ordering: '-created_at' }),
    enabled: auth.isAuthenticated,
  });
  const publicProfileQuery = useQuery({
    ...publicUserQueries.publicProfile(publicUserId),
    enabled: auth.isAuthenticated && Number.isFinite(publicUserId) && publicUserId > 0,
  });

  const days = useMemo(() => buildYearDays(selectedYear), [selectedYear]);
  const fallbackMarkCalendar = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of subjectsQuery.data?.results ?? []) {
      const createdAt = typeof item.created_at === 'string' ? item.created_at : '';
      const date = toLocalDateKey(createdAt);
      if (date.startsWith(String(selectedYear))) {
        counts.set(date, (counts.get(date) ?? 0) + 1);
      }
    }
    return counts;
  }, [selectedYear, subjectsQuery.data?.results]);
  const markCalendar = statsQuery.data?.mark_calendar;
  const countByDate = useMemo(() => {
    if (markCalendar?.length) {
      return new Map(markCalendar.map((item) => [item.date, item.count]));
    }
    return fallbackMarkCalendar;
  }, [fallbackMarkCalendar, markCalendar]);
  const profileTotals = {
    subjects: statsQuery.data?.totals.subjects || subjectsQuery.data?.count || 0,
    reviews: statsQuery.data?.totals.reviews || reviewsQuery.data?.count || 0,
    collections: statsQuery.data?.totals.collections || collectionsQuery.data?.count || 0,
    marksInYear:
      statsQuery.data?.totals.marks_in_year ||
      [...fallbackMarkCalendar.values()].reduce((total, count) => total + count, 0),
  };
  const publicStats = publicProfileQuery.data?.stats;
  const activityItems = useMemo(
    () => activityQuery.data?.pages.flatMap((page) => page.results) ?? [],
    [activityQuery.data?.pages],
  );
  const yearOptions = useMemo(() => {
    const years = new Set([currentYear, selectedYear, ...(statsQuery.data?.available_years ?? [])]);
    return [...years].sort((a, b) => b - a);
  }, [currentYear, selectedYear, statsQuery.data?.available_years]);
  const monthPositions = useMemo(
    () =>
      monthLabels.map((label, month) => ({
        label,
        week: getWeekIndex(`${selectedYear}-${String(month + 1).padStart(2, '0')}-01`),
      })),
    [selectedYear],
  );

  function updateProfileParams(values: Record<string, string | null>) {
    setSearchParams((currentParams) => {
      const nextParams = new URLSearchParams(currentParams);
      Object.entries(values).forEach(([key, value]) => {
        if (value) nextParams.set(key, value);
        else nextParams.delete(key);
      });
      return nextParams;
    });
  }

  if (auth.status === 'checking') {
    return (
      <Page title={t('me.dashboard.profile')} eyebrow={t('nav.groupOverview')}>
        <LoadingState title={t('me.dashboard.checking')} />
      </Page>
    );
  }

  if (auth.role === 'guest') {
    return <Navigate replace to={routes.login} />;
  }

  return (
    <Page
      title={profile?.nickname ?? t('me.dashboard.profile')}
      eyebrow={t('nav.groupOverview')}
      description={profile?.bio || undefined}
    >
      <div className="grid min-w-0 gap-8 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="grid content-start gap-5">
          <section className="lg:sticky lg:top-6">
            <div className="flex items-center gap-4 lg:block">
              <img
                className="size-24 rounded-full bg-[var(--color-surface-muted)] object-cover ring-1 ring-[var(--color-border)] lg:size-32"
                src={profile?.avatar || avatarPlaceholder}
                alt=""
              />
              <div className="min-w-0 lg:mt-5">
                <h2 className="truncate text-2xl font-semibold tracking-tight text-[var(--color-text)]">
                  {profile?.nickname}
                </h2>
                <p className="mt-1 truncate text-sm text-neutral-500 dark:text-neutral-400">{profile?.email}</p>
                {profile?.bio ? (
                  <p className="mt-3 line-clamp-4 text-sm leading-6 text-neutral-600 dark:text-neutral-300 lg:line-clamp-none">
                    {profile.bio}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="mt-5 grid gap-2">
              {profile?.user_id ? (
                <Button asChild className="w-full" type="button">
                  <Link to={routes.userProfile(profile.user_id)}>
                    <ExternalLink className="size-4" />
                    {t('me.dashboard.viewPublicProfile')}
                  </Link>
                </Button>
              ) : null}
              <Button asChild className="w-full" type="button" variant="secondary">
                <Link to={routes.settings}>
                  <Settings className="size-4" />
                  {t('me.dashboard.editProfile')}
                </Link>
              </Button>
            </div>

            {profile?.user_id ? (
              <div className="mt-5 flex flex-wrap gap-2">
                <Link
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm text-[var(--color-text-muted)] shadow-sm transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-accent-strong)]"
                  to={routes.userFollowers(profile.user_id)}
                >
                  <Users className="size-4" />
                  <strong className="font-semibold text-[var(--color-text)]">{publicStats?.follower_count ?? 0}</strong>
                  <span>{t('profile.followers')}</span>
                </Link>
                <Link
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm text-[var(--color-text-muted)] shadow-sm transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-accent-strong)]"
                  to={routes.userFollowing(profile.user_id)}
                >
                  <Users className="size-4" />
                  <strong className="font-semibold text-[var(--color-text)]">
                    {publicStats?.following_count ?? 0}
                  </strong>
                  <span>{t('profile.followingCount')}</span>
                </Link>
              </div>
            ) : null}

            <nav className="mt-5 grid gap-1 border-t border-[var(--color-border)] pt-4 text-sm">
              <Link
                className="flex items-center justify-between gap-3 rounded-lg px-2 py-2 text-[var(--color-text-muted)] transition hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]"
                to={routes.library}
              >
                <span className="inline-flex items-center gap-2">
                  <Library className="size-4" />
                  {t('me.dashboard.subjects')}
                </span>
                <strong className="font-semibold text-[var(--color-text)]">{profileTotals.subjects}</strong>
              </Link>
              <Link
                className="flex items-center justify-between gap-3 rounded-lg px-2 py-2 text-[var(--color-text-muted)] transition hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]"
                to={routes.reviews}
              >
                <span className="inline-flex items-center gap-2">
                  <FileText className="size-4" />
                  {t('me.dashboard.reviews')}
                </span>
                <strong className="font-semibold text-[var(--color-text)]">{profileTotals.reviews}</strong>
              </Link>
              <Link
                className="flex items-center justify-between gap-3 rounded-lg px-2 py-2 text-[var(--color-text-muted)] transition hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]"
                to={routes.collections}
              >
                <span className="inline-flex items-center gap-2">
                  <Layers3 className="size-4" />
                  {t('me.dashboard.collections')}
                </span>
                <strong className="font-semibold text-[var(--color-text)]">{profileTotals.collections}</strong>
              </Link>
            </nav>
          </section>
        </aside>

        <main className="grid min-w-0 content-start gap-8">
          <section className="grid min-w-0 gap-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">
                {t('me.dashboard.latestReviews')}
              </h2>
              <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.reviews}>
                {t('me.dashboard.viewAll')}
              </Link>
            </div>
            <div className="grid min-w-0 gap-3 md:grid-cols-3">
              {(reviewsQuery.data?.results ?? []).map((review) => (
                <Link
                  className="min-w-0 rounded-lg border border-[var(--color-border)] p-4 transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)]"
                  key={review.id}
                  to={review.subject ? routes.subject(review.subject.id) : routes.reviews}
                >
                  <h3 className="line-clamp-1 text-sm font-semibold text-neutral-950 dark:text-white">
                    {review.title}
                  </h3>
                  <p className="mt-1 line-clamp-1 text-xs text-neutral-500 dark:text-neutral-400">
                    {review.subject?.display_title || review.subject?.title || t('me.dashboard.untitledSubject')}
                  </p>
                  <p className="mt-3 line-clamp-3 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
                    {review.content || t('me.dashboard.noContent')}
                  </p>
                </Link>
              ))}
              {!reviewsQuery.isLoading && (reviewsQuery.data?.results.length ?? 0) === 0 ? (
                <div className="rounded-lg border border-dashed border-[var(--color-border)] p-6 text-sm text-[var(--color-text-muted)] md:col-span-3">
                  {t('me.dashboard.noReviews')}
                </div>
              ) : null}
            </div>
          </section>

          <section className="grid min-w-0 gap-5">
            <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_104px]">
              <div className="min-w-0 rounded-lg border border-[var(--color-border)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="size-4 text-neutral-400" />
                    <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">
                      {profileTotals.marksInYear} {t('me.dashboard.marksIn')} {selectedYear}
                    </h2>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
                    <span>{t('me.dashboard.less')}</span>
                    {[0, 1, 3, 6, 8].map((count) => (
                      <span className={`size-3 rounded-[3px] ${heatClass(count)}`} key={count} />
                    ))}
                    <span>{t('me.dashboard.more')}</span>
                  </div>
                </div>
                <div className="mt-4 overflow-x-auto pb-2">
                  <div className="min-w-[760px]">
                    <div className="relative mb-2 h-4 text-[11px] text-neutral-400">
                      {monthPositions.map((month) => (
                        <span className="absolute" key={month.label} style={{ left: `${month.week * 18}px` }}>
                          {month.label}
                        </span>
                      ))}
                    </div>
                    <div className="grid grid-flow-col grid-rows-7 gap-1" style={{ gridAutoColumns: '14px' }}>
                      {days.map((day) => {
                        const count = countByDate.get(day) ?? 0;
                        return (
                          <span
                            aria-label={`${day}: ${count} marks`}
                            className={`grid size-3.5 place-items-center rounded-[3px] text-[9px] font-semibold leading-none ${heatClass(count)}`}
                            key={day}
                            title={`${day}: ${count} marks`}
                          >
                            {count > 0 ? (count > 9 ? '9+' : count) : ''}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>

              <nav className="grid content-start gap-1">
                {yearOptions.map((year) => (
                  <button
                    className={`rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                      year === selectedYear
                        ? 'bg-[var(--color-accent)] text-[var(--color-accent-contrast)]'
                        : 'text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]'
                    }`}
                    key={year}
                    type="button"
                    onClick={() => updateProfileParams({ year: String(year) })}
                  >
                    {year}
                  </button>
                ))}
              </nav>
            </div>

            <div className="grid min-w-0 gap-4">
              <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">
                {t('me.dashboard.activity')}
              </h2>
              {activityQuery.isLoading ? <LoadingState title={t('me.dashboard.loadingActivity')} /> : null}
              <div className="grid gap-0">
                {activityItems.map((activity) => (
                  <article
                    className="relative grid grid-cols-[24px_minmax(0,1fr)] gap-3 border-l border-[var(--color-border)] pb-5 pl-4 last:pb-0"
                    key={activity.id}
                  >
                    <span className="absolute -left-[5px] top-1 size-2.5 rounded-full border-2 border-white bg-neutral-300 dark:border-neutral-950 dark:bg-neutral-700" />
                    <span className="text-xs text-neutral-400">{formatDate(activity.created_at)}</span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-neutral-950 dark:text-white">
                        {activityTitle(activity)}
                      </p>
                      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                        {activity.activity_type.replaceAll('_', ' ')}
                      </p>
                      {activity.subject ? (
                        <Link
                          className="mt-3 grid min-w-0 grid-cols-[48px_minmax(0,1fr)] gap-3 rounded-lg border border-[var(--color-border)] p-2 transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)]"
                          to={routes.subject(activity.subject.id)}
                        >
                          <img
                            className="h-16 w-12 rounded-md bg-[var(--color-surface-muted)] object-cover"
                            src={activity.subject.image_thumbnail || activity.subject.image || coverPlaceholder}
                            alt=""
                          />
                          <span className="grid min-w-0 content-center gap-1">
                            <span className="line-clamp-1 text-sm font-semibold text-neutral-950 dark:text-white">
                              {activity.subject.display_title || activity.subject.title}
                            </span>
                            <span className="line-clamp-1 text-xs text-neutral-500 dark:text-neutral-400">
                              {activity.subject.display_subtitle || activity.subject.subject_type}
                            </span>
                          </span>
                        </Link>
                      ) : null}
                    </div>
                  </article>
                ))}
                {!activityQuery.isLoading && activityItems.length === 0 ? (
                  <EmptyState
                    title={t('me.dashboard.noActivityTitle')}
                    description={t('me.dashboard.noActivityBody')}
                  />
                ) : null}
              </div>
              {!activityQuery.isLoading && activityItems.length > 0 ? (
                <div className="community-load-more">
                  {activityQuery.hasNextPage ? (
                    <Button
                      disabled={activityQuery.isFetchingNextPage}
                      type="button"
                      variant="secondary"
                      onClick={() => void activityQuery.fetchNextPage()}
                    >
                      {activityQuery.isFetchingNextPage ? t('me.dashboard.loadingMore') : t('me.dashboard.loadMore')}
                    </Button>
                  ) : (
                    <span>{t('me.dashboard.activityEnd')}</span>
                  )}
                </div>
              ) : null}
            </div>
          </section>
        </main>
      </div>
    </Page>
  );
}
