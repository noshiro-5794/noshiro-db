import { useMemo } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { CalendarDays, FileText, Layers3, Library } from 'lucide-react';
import { profileApi } from '@/features/auth/api';
import { useAuth } from '@/features/auth/use-auth';
import type { Locale } from '@/features/i18n/messages';
import { useI18n } from '@/features/i18n/use-i18n';
import { libraryQueries } from '@/features/library/library-queries';
import { socialQueries } from '@/features/social/social-queries';
import { routes } from '@/routes/paths';
import { EmptyState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const avatarPlaceholder = '/assets/placeholders/avatar.png';
const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const activityPageSize = 8;
const monthLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const labels: Record<Locale, Record<string, string>> = {
  'zh-CN': {
    profile: '个人主页',
    loading: '正在加载个人主页',
    checking: '正在检查会话',
    description: '你的动态、标记和长评会展示在这里。',
    editProfile: '编辑资料',
    subjects: '标记',
    reviews: '长评',
    collections: '收藏集',
    latestReviews: '最新长评',
    viewAll: '查看全部',
    untitledSubject: '未命名作品',
    noContent: '暂无内容。',
    noReviews: '还没有长评。',
    marksIn: '个标记于',
    less: '少',
    more: '多',
    activity: '贡献动态',
    noActivityTitle: '暂无动态。',
    noActivityBody: '标记作品或撰写长评后，这里会形成时间线。',
    loadingActivity: '正在加载动态',
  },
  'en-US': {
    profile: 'Profile',
    loading: 'Loading your workspace profile.',
    checking: 'Checking session',
    description: 'Your activity, marks, and reviews appear here.',
    editProfile: 'Edit profile',
    subjects: 'Subjects',
    reviews: 'Reviews',
    collections: 'Collections',
    latestReviews: 'Latest reviews',
    viewAll: 'View all',
    untitledSubject: 'Untitled subject',
    noContent: 'No content.',
    noReviews: 'No reviews yet.',
    marksIn: 'marks in',
    less: 'Less',
    more: 'More',
    activity: 'Contribution activity',
    noActivityTitle: 'No activity yet.',
    noActivityBody: 'Mark subjects or write reviews to build your timeline.',
    loadingActivity: 'Loading activity',
  },
  'ja-JP': {
    profile: 'プロフィール',
    loading: 'プロフィールを読み込んでいます。',
    checking: 'セッションを確認中',
    description: 'アクティビティ、マーク、レビューがここに表示されます。',
    editProfile: 'プロフィールを編集',
    subjects: '記録',
    reviews: 'レビュー',
    collections: 'コレクション',
    latestReviews: '最新レビュー',
    viewAll: 'すべて表示',
    untitledSubject: '無題の作品',
    noContent: '内容はありません。',
    noReviews: 'レビューはまだありません。',
    marksIn: '件のマーク:',
    less: '少',
    more: '多',
    activity: '貢献アクティビティ',
    noActivityTitle: 'アクティビティはまだありません。',
    noActivityBody: '作品を記録したりレビューを書くと、ここにタイムラインが作られます。',
    loadingActivity: 'アクティビティを読み込み中',
  },
};

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
  if (count <= 0) return 'bg-neutral-100 text-transparent dark:bg-neutral-900';
  if (count === 1) return 'bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]';
  if (count <= 3) return 'bg-[var(--color-accent)] text-white opacity-60';
  if (count <= 6) return 'bg-[var(--color-accent)] text-white opacity-80';
  return 'bg-[var(--color-accent)] text-[var(--color-accent-contrast)]';
}

function activityTitle(activity: {
  activity_type: string;
  subject?: { display_title?: string; title?: string; display_subtitle?: string; image_thumbnail?: string | null; image?: string | null } | null;
  review?: { title: string } | null;
  collection?: { name: string } | null;
}) {
  return activity.subject?.display_title || activity.subject?.title || activity.review?.title || activity.collection?.name || activity.activity_type.replaceAll('_', ' ');
}

export function MePage() {
  const auth = useAuth();
  const { locale, t } = useI18n();
  const copy = labels[locale];
  const [searchParams, setSearchParams] = useSearchParams();
  const currentYear = new Date().getFullYear();
  const selectedYear = Number(searchParams.get('year') ?? currentYear) || currentYear;
  const activityPage = Math.max(1, Number(searchParams.get('activity_page') ?? '1') || 1);
  const profile = auth.profile;
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
  const activityQuery = useQuery({
    ...socialQueries.myActivities({ page: activityPage, page_size: activityPageSize, ordering: '-created_at' }),
    enabled: auth.isAuthenticated,
  });
  const reviewsQuery = useQuery({
    ...libraryQueries.reviews({ page_size: 3, ordering: '-created_at' }),
    enabled: auth.isAuthenticated,
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
  const countByDate = useMemo(() => {
    if (statsQuery.data?.mark_calendar.length) {
      return new Map(statsQuery.data.mark_calendar.map((item) => [item.date, item.count]));
    }
    return fallbackMarkCalendar;
  }, [fallbackMarkCalendar, statsQuery.data?.mark_calendar]);
  const profileTotals = {
    subjects: statsQuery.data?.totals.subjects || subjectsQuery.data?.count || 0,
    reviews: statsQuery.data?.totals.reviews || reviewsQuery.data?.count || 0,
    collections: statsQuery.data?.totals.collections || collectionsQuery.data?.count || 0,
    marksInYear: statsQuery.data?.totals.marks_in_year || [...fallbackMarkCalendar.values()].reduce((total, count) => total + count, 0),
  };
  const activityTotalPages = Math.max(1, Math.ceil((activityQuery.data?.count ?? 0) / activityPageSize));
  const yearOptions = useMemo(() => {
    const years = new Set([currentYear, selectedYear, ...(statsQuery.data?.available_years ?? [])]);
    return [...years].sort((a, b) => b - a);
  }, [currentYear, selectedYear, statsQuery.data?.available_years]);
  const monthPositions = useMemo(() => monthLabels.map((label, month) => ({ label, week: getWeekIndex(`${selectedYear}-${String(month + 1).padStart(2, '0')}-01`) })), [selectedYear]);

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
      <Page title={copy.profile} description={copy.loading}>
        <LoadingState title={copy.checking} />
      </Page>
    );
  }

  if (auth.role === 'guest') {
    return <Navigate replace to={routes.login} />;
  }

  return (
    <Page title={profile?.nickname ?? copy.profile} eyebrow={copy.profile} description={profile?.bio || copy.description}>
      <div className="grid min-w-0 gap-8 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="grid content-start gap-5">
          <img
            className="size-32 rounded-full bg-neutral-100 object-cover ring-1 ring-neutral-200 dark:bg-neutral-900 dark:ring-neutral-800"
            src={profile?.avatar || avatarPlaceholder}
            alt=""
          />
          <div className="grid gap-1">
            <h2 className="text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">{profile?.nickname}</h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">{profile?.email}</p>
            {profile?.bio ? <p className="mt-3 text-sm leading-6 text-neutral-600 dark:text-neutral-300">{profile.bio}</p> : null}
          </div>
          <Link className="button button-secondary w-full" to={routes.settings}>
            {copy.editProfile}
          </Link>
          {profile?.user_id ? (
            <div className="grid grid-cols-2 gap-2">
              <Link className="button button-secondary w-full" to={routes.userFollowers(profile.user_id)}>
                {t('profile.followersTitle')}
              </Link>
              <Link className="button button-secondary w-full" to={routes.userFollowing(profile.user_id)}>
                {t('profile.followingTitle')}
              </Link>
            </div>
          ) : null}
          <div className="grid gap-3 border-t border-neutral-200 pt-4 text-sm dark:border-neutral-800">
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
                <Library className="size-4" />
                {copy.subjects}
              </span>
              <strong className="text-neutral-950 dark:text-white">{profileTotals.subjects}</strong>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
                <FileText className="size-4" />
                {copy.reviews}
              </span>
              <strong className="text-neutral-950 dark:text-white">{profileTotals.reviews}</strong>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
                <Layers3 className="size-4" />
                {copy.collections}
              </span>
              <strong className="text-neutral-950 dark:text-white">{profileTotals.collections}</strong>
            </div>
          </div>
        </aside>

        <main className="grid min-w-0 content-start gap-8">
          <section className="grid min-w-0 gap-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{copy.latestReviews}</h2>
              <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.reviews}>
                {copy.viewAll}
              </Link>
            </div>
            <div className="grid min-w-0 gap-3 md:grid-cols-3">
              {(reviewsQuery.data?.results ?? []).map((review) => (
                <Link
                  className="min-w-0 rounded-lg border border-neutral-200 p-4 transition hover:border-[var(--color-accent-border)] dark:border-neutral-800"
                  key={review.id}
                  to={review.subject ? routes.subject(review.subject.id) : routes.reviews}
                >
                  <h3 className="line-clamp-1 text-sm font-semibold text-neutral-950 dark:text-white">{review.title}</h3>
                  <p className="mt-1 line-clamp-1 text-xs text-neutral-500 dark:text-neutral-400">
                    {review.subject?.display_title || review.subject?.title || copy.untitledSubject}
                  </p>
                  <p className="mt-3 line-clamp-3 text-sm leading-6 text-neutral-600 dark:text-neutral-300">{review.content || copy.noContent}</p>
                </Link>
              ))}
              {!reviewsQuery.isLoading && (reviewsQuery.data?.results.length ?? 0) === 0 ? (
                <div className="rounded-lg border border-dashed border-neutral-200 p-6 text-sm text-neutral-500 dark:border-neutral-800 dark:text-neutral-400 md:col-span-3">
                  {copy.noReviews}
                </div>
              ) : null}
            </div>
          </section>

          <section className="grid min-w-0 gap-5">
            <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_104px]">
              <div className="min-w-0 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="size-4 text-neutral-400" />
                    <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">
                      {profileTotals.marksInYear} {copy.marksIn} {selectedYear}
                    </h2>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
                    <span>{copy.less}</span>
                    {[0, 1, 3, 6, 8].map((count) => (
                      <span className={`size-3 rounded-[3px] ${heatClass(count)}`} key={count} />
                    ))}
                    <span>{copy.more}</span>
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
                        : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-950 dark:text-neutral-400 dark:hover:bg-neutral-900 dark:hover:text-white'
                    }`}
                    key={year}
                    type="button"
                    onClick={() => updateProfileParams({ year: String(year), activity_page: null })}
                  >
                    {year}
                  </button>
                ))}
              </nav>
            </div>

            <div className="grid min-w-0 gap-4">
              <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{copy.activity}</h2>
              {activityQuery.isLoading ? <LoadingState title={copy.loadingActivity} /> : null}
              <div className="grid gap-0">
                {(activityQuery.data?.results ?? []).map((activity) => (
                  <article className="relative grid grid-cols-[24px_minmax(0,1fr)] gap-3 border-l border-neutral-200 pb-5 pl-4 last:pb-0 dark:border-neutral-800" key={activity.id}>
                    <span className="absolute -left-[5px] top-1 size-2.5 rounded-full border-2 border-white bg-neutral-300 dark:border-neutral-950 dark:bg-neutral-700" />
                    <span className="text-xs text-neutral-400">{formatDate(activity.created_at)}</span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-neutral-950 dark:text-white">{activityTitle(activity)}</p>
                      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{activity.activity_type.replaceAll('_', ' ')}</p>
                      {activity.subject ? (
                        <Link className="mt-3 grid min-w-0 grid-cols-[48px_minmax(0,1fr)] gap-3 rounded-lg border border-neutral-200 p-2 transition hover:border-[var(--color-accent-border)] dark:border-neutral-800" to={routes.subject(activity.subject.id)}>
                          <img
                            className="h-16 w-12 rounded-md bg-neutral-100 object-cover dark:bg-neutral-900"
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
                {!activityQuery.isLoading && (activityQuery.data?.results.length ?? 0) === 0 ? (
                  <EmptyState title={copy.noActivityTitle} description={copy.noActivityBody} />
                ) : null}
              </div>
              <Pagination currentPage={activityPage} totalPages={activityTotalPages} onPageChange={(page) => updateProfileParams({ activity_page: String(page) })} />
            </div>
          </section>
        </main>
      </div>
    </Page>
  );
}
