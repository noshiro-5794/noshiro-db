import { useMemo } from 'react';
import { getRouteApi, Link, Navigate } from '@tanstack/react-router';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { ArrowRight, FileText, Layers3, Library, Settings, UserRound } from 'lucide-react';
import { profileApi, useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { libraryQueries } from '@/entities/library';
import { communityActivitiesApi } from '@/entities/community';
import { communityQueryKeys } from '@/entities/community';
import { publicUserQueries } from '@/entities/user';
import { ContributionCalendar, ProfileActivityTimeline } from '@/features/profile-dashboard';
import { getNextApiPageParam } from '@/shared/api';
import { formatDate } from '@/shared/lib/date';
import { routes } from '@/shared/routing/paths';
import { Avatar } from '@/shared/ui/Avatar';
import { Button } from '@/shared/ui/Button';
import { ListSurface, ResultsState, type ResultsStatus } from '@/shared/ui/DataView';
import { DetailSection } from '@/shared/ui/Detail';
import { LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

const activityPageSize = 8;
const meRoute = getRouteApi('/me');

function getBrowserTimeZone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
}

function resultsStatus(isLoading: boolean, isError: boolean, itemCount: number): ResultsStatus {
  if (isLoading) return 'loading';
  if (isError) return 'error';
  return itemCount === 0 ? 'empty' : 'ready';
}

export function MePage() {
  const auth = useAuth();
  const { t } = useI18n();
  const navigate = meRoute.useNavigate();
  const search = meRoute.useSearch();
  const currentYear = new Date().getFullYear();
  const selectedYear = search.year ?? currentYear;
  const profile = auth.profile;
  const publicUserId = profile?.user_id ?? 0;
  const browserTimeZone = useMemo(() => getBrowserTimeZone(), []);

  const statsQuery = useQuery({
    queryKey: ['profile', 'stats', selectedYear, browserTimeZone],
    queryFn: ({ signal }) => profileApi.getStats({ year: selectedYear, timezone: browserTimeZone }, { signal }),
    enabled: auth.isAuthenticated,
  });
  const subjectsCountQuery = useQuery({
    ...libraryQueries.userSubjects({ page_size: 1 }),
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
    queryFn: ({ pageParam, signal }) =>
      communityActivitiesApi.listMine(
        { page: pageParam, page_size: activityPageSize, ordering: '-created_at' },
        { signal },
      ),
    initialPageParam: 1,
    getNextPageParam: getNextApiPageParam,
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

  const profileTotals: Record<'collections' | 'marksInYear' | 'reviews' | 'subjects', number | undefined> = {
    subjects: statsQuery.data?.totals.subjects ?? subjectsCountQuery.data?.count,
    reviews: statsQuery.data?.totals.reviews ?? reviewsQuery.data?.count,
    collections: statsQuery.data?.totals.collections ?? collectionsQuery.data?.count,
    marksInYear: statsQuery.data?.totals.marks_in_year,
  };
  const publicStats = publicProfileQuery.data?.stats;
  const reviews = reviewsQuery.data?.results ?? [];
  const reviewsStatus = resultsStatus(reviewsQuery.isLoading, reviewsQuery.isError, reviews.length);
  const activityItems = useMemo(
    () => activityQuery.data?.pages.flatMap((page) => page.results) ?? [],
    [activityQuery.data?.pages],
  );
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
      headerMode="context"
      seoDescription={profile?.bio || undefined}
    >
      <div className="grid min-w-0 gap-8 xl:grid-cols-[232px_minmax(0,1fr)]" data-slot="profile-dashboard">
        <aside className="min-w-0" data-slot="profile-dashboard-sidebar">
          <section
            className="xl:sticky xl:top-[calc(var(--ui-sticky-content-top)+1.25rem)]"
            data-slot="profile-summary"
          >
            <div className="flex min-w-0 items-center gap-4 xl:grid">
              <Avatar
                alt={profile?.nickname ?? t('me.dashboard.profile')}
                className="size-20 xl:size-24"
                fallback={profile?.nickname.slice(0, 1)}
                loading="eager"
                src={profile?.avatar}
              />
              <div className="min-w-0 xl:mt-1">
                <h1 className="m-0 truncate text-xl font-semibold leading-tight text-foreground">
                  {profile?.nickname ?? t('me.dashboard.profile')}
                </h1>
                <p className="mt-1 truncate text-xs text-subtle-foreground">{profile?.email}</p>
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted-foreground xl:line-clamp-none">
                  {profile?.bio || t('profile.noBio')}
                </p>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-2 xl:grid-cols-1" data-slot="profile-actions">
              <Button asChild className="w-full" type="button">
                <Link to={routes.settings}>
                  <Settings className="size-4" />
                  {t('me.dashboard.editProfile')}
                </Link>
              </Button>
              {profile?.user_id ? (
                <Button asChild className="w-full" type="button" variant="secondary">
                  <Link params={{ userId: String(profile.user_id) }} to="/users/$userId">
                    <UserRound className="size-4" />
                    {t('me.dashboard.viewPublicProfile')}
                  </Link>
                </Button>
              ) : null}
            </div>

            {profile?.user_id ? (
              <div className="mt-5 grid grid-cols-2 rounded-sm bg-muted px-3 py-2.5" data-slot="profile-connections">
                <Link
                  className="group grid min-w-0 gap-0.5 border-r border-border-subtle pr-3 transition-colors hover:text-[var(--ui-accent-text)]"
                  params={{ userId: String(profile.user_id) }}
                  to="/users/$userId/followers"
                >
                  <strong className="text-base font-semibold tabular-nums text-foreground group-hover:text-[var(--ui-accent-text)]">
                    {publicStats?.follower_count ?? '—'}
                  </strong>
                  <span className="truncate text-xs text-muted-foreground">{t('profile.followers')}</span>
                </Link>
                <Link
                  className="group grid min-w-0 gap-0.5 pl-3 transition-colors hover:text-[var(--ui-accent-text)]"
                  params={{ userId: String(profile.user_id) }}
                  to="/users/$userId/following"
                >
                  <strong className="text-base font-semibold tabular-nums text-foreground group-hover:text-[var(--ui-accent-text)]">
                    {publicStats?.following_count ?? '—'}
                  </strong>
                  <span className="truncate text-xs text-muted-foreground">{t('profile.followingCount')}</span>
                </Link>
              </div>
            ) : null}

            <nav
              aria-label={t('me.dashboard.profile')}
              className="mt-3 grid divide-y divide-border-subtle overflow-hidden rounded-sm bg-muted px-2 text-sm"
              data-slot="profile-dashboard-navigation"
            >
              {[
                {
                  icon: Library,
                  label: t('me.dashboard.subjects'),
                  to: routes.library,
                  value: profileTotals.subjects,
                },
                {
                  icon: FileText,
                  label: t('me.dashboard.reviews'),
                  to: routes.reviews,
                  value: profileTotals.reviews,
                },
                {
                  icon: Layers3,
                  label: t('me.dashboard.collections'),
                  to: routes.collections,
                  value: profileTotals.collections,
                },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    className="group flex min-h-10 items-center justify-between gap-3 px-1 text-muted-foreground transition-colors hover:text-foreground"
                    key={item.to}
                    to={item.to}
                  >
                    <span className="inline-flex min-w-0 items-center gap-2">
                      <Icon className="size-4 shrink-0 text-subtle-foreground" />
                      <span className="truncate">{item.label}</span>
                    </span>
                    <strong className="font-semibold tabular-nums text-foreground">{item.value ?? '—'}</strong>
                  </Link>
                );
              })}
            </nav>
          </section>
        </aside>

        <div className="grid min-w-0 content-start gap-6" data-slot="profile-dashboard-content">
          <DetailSection
            actions={
              <Link
                className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground transition-colors hover:text-[var(--ui-accent-text)]"
                to={routes.reviews}
              >
                {t('me.dashboard.viewAll')} <ArrowRight className="size-4" />
              </Link>
            }
            className="border-t-0 pt-0"
            meta={reviewsQuery.data ? `${reviewsQuery.data.count} ${t('common.items')}` : undefined}
            title={t('me.dashboard.latestReviews')}
            titleId="profile-latest-reviews"
          >
            <ResultsState
              emptyTitle={t('me.dashboard.noReviews')}
              errorDescription={t('search.errorBody')}
              errorTitle={t('reviews.errorTitle')}
              loadingTitle={t('profile.loadingReviews')}
              status={reviewsStatus}
            >
              <ListSurface>
                {reviews.map((review) => (
                  <Link
                    className="group grid min-w-0 gap-2 border-b border-border-subtle px-3 py-3 transition-colors last:border-b-0 hover:bg-muted sm:px-4"
                    data-slot="profile-review-row"
                    key={review.id}
                    to={routes.review(review.id)}
                  >
                    <div className="flex min-w-0 items-start justify-between gap-3">
                      <h3 className="m-0 line-clamp-1 text-sm font-semibold text-foreground transition-colors group-hover:text-[var(--ui-accent-text)]">
                        {review.title}
                      </h3>
                      {review.updated_at || review.created_at ? (
                        <time
                          className="shrink-0 text-xs text-subtle-foreground"
                          dateTime={review.updated_at || review.created_at}
                        >
                          {formatDate(review.updated_at || review.created_at)}
                        </time>
                      ) : null}
                    </div>
                    <p className="line-clamp-1 text-xs text-muted-foreground">
                      {review.subject?.display_title ||
                        review.subject?.title ||
                        review.subject?.title_cn ||
                        t('me.dashboard.untitledSubject')}
                    </p>
                    <p className="line-clamp-2 text-sm leading-6 text-muted-foreground">
                      {review.content || t('me.dashboard.noContent')}
                    </p>
                  </Link>
                ))}
              </ListSurface>
            </ResultsState>
          </DetailSection>

          <DetailSection
            meta={
              profileTotals.marksInYear === undefined
                ? undefined
                : `${profileTotals.marksInYear} ${t('me.dashboard.marksIn')} ${selectedYear}`
            }
            title={t('me.dashboard.activity')}
            titleId="profile-contribution-activity"
          >
            <ContributionCalendar
              availableYears={statsQuery.data?.available_years ?? []}
              isError={statsQuery.isError}
              isLoading={statsQuery.isLoading}
              markCalendar={statsQuery.data?.mark_calendar ?? []}
              marksInYear={profileTotals.marksInYear ?? 0}
              selectedYear={selectedYear}
              onYearChange={(year) =>
                void navigate({ search: (current) => ({ ...current, year: year === currentYear ? undefined : year }) })
              }
            />

            <div className="border-t border-border-subtle pt-5" data-slot="profile-activity-stream">
              <ProfileActivityTimeline
                activities={activityItems}
                hasNextPage={activityQuery.hasNextPage}
                isError={activityQuery.isError}
                isFetchingNextPage={activityQuery.isFetchingNextPage}
                isLoading={activityQuery.isLoading}
                onLoadMore={() => {
                  void activityQuery.fetchNextPage();
                }}
              />
            </div>
          </DetailSection>
        </div>
      </div>
    </Page>
  );
}
