import { Link } from 'react-router-dom';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CalendarDays, Layers3, Library, MessageSquare, Settings, ShieldCheck } from 'lucide-react';
import { CalendarBoard } from '@/features/calendar/components/CalendarBoard';
import { CommunityCommentsSection } from '@/features/community/components/CommunityCommentsSection';
import { CommunityContentCard } from '@/features/community/components/CommunityContentCard';
import { CommunityTargetActions } from '@/features/community/components/CommunityTargetActions';
import { communityQueries } from '@/features/community/community-queries';
import { SearchShowcase } from '@/features/home/components/SearchShowcase';
import { libraryQueries } from '@/features/library/library-queries';
import { subjectQueries } from '@/features/subjects/subject-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import type { Activity, CurrentUserProfile, UserSubject } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';

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

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function subjectTitle(item: UserSubject, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

function statusLabel(status: string | undefined, t: ReturnType<typeof useI18n>['t']) {
  const labels: Record<string, string> = {
    wish: t('status.wish'),
    doing: t('status.doing'),
    done: t('status.done'),
    on_hold: t('status.onHold'),
    drop: t('status.drop'),
  };
  return labels[status ?? ''] ?? status?.replaceAll('_', ' ') ?? t('status.marked');
}

function activityHref(activity: Activity) {
  if (activity.post?.id) return routes.communityPost(activity.post.id);
  if (activity.review?.id) return routes.review(activity.review.id);
  if (activity.collection?.id) return routes.collections;
  if (activity.subject?.id) return routes.subject(activity.subject.id);
  return routes.home;
}

function activityTypeLabel(type: string, t: ReturnType<typeof useI18n>['t']) {
  if (type === 'post_created') return t('home.activity.postCreated');
  if (type === 'user_subject_created') return t('home.activity.subjectMarked');
  if (type === 'user_subject_updated') return t('home.activity.subjectUpdated');
  if (type === 'review_created') return t('home.activity.reviewCreated');
  if (type === 'collection_created') return t('home.activity.collectionCreated');
  if (type === 'collection_item_added') return t('home.activity.collectionItemAdded');
  if (type === 'comment_created') return t('home.activity.commentCreated');
  if (type === 'user_followed') return t('home.activity.userFollowed');
  return type.replaceAll('_', ' ');
}

function activityTitle(activity: Activity, fallback: string) {
  return (
    activity.subject?.display_title
    || activity.subject?.title
    || activity.review?.title
    || activity.collection?.name
    || activity.target_user?.nickname
    || activity.post?.content?.split('\n').find(Boolean)?.slice(0, 96)
    || activity.comment?.content?.split('\n').find(Boolean)?.slice(0, 96)
    || fallback
  );
}

function activityBody(activity: Activity, t: ReturnType<typeof useI18n>['t']) {
  return (
    activity.message
    || activity.post?.content
    || activity.comment?.content
    || activity.review?.content
    || activity.collection?.note
    || activity.target_user?.nickname
    || activity.subject?.display_subtitle
    || activity.subject?.platform
    || t('common.noContent')
  );
}

export function UserHome({ isAdmin, profile }: UserHomeProps) {
  const { t } = useI18n();
  const [expandedActivityId, setExpandedActivityId] = useState<number | null>(null);
  const feedQuery = useQuery(communityQueries.feed({ page_size: 5, include_self: true, ordering: '-created_at' }));
  const recentSubjectsQuery = useQuery(libraryQueries.userSubjects({ page_size: 4, ordering: '-updated_at' }));
  const watchingSubjectsQuery = useQuery(libraryQueries.userSubjects({ status: 'doing', page_size: 3, ordering: '-updated_at' }));
  const reviewsQuery = useQuery(libraryQueries.reviews({ page_size: 3, ordering: '-created_at' }));
  const collectionsQuery = useQuery(libraryQueries.collections({ page_size: 4, ordering: '-id' }));
  const recentSubjects = recentSubjectsQuery.data?.results ?? [];
  const feedItems = (feedQuery.data?.results ?? []).slice(0, 5);
  const watchingSubjects = watchingSubjectsQuery.data?.results ?? [];
  const reviews = (reviewsQuery.data?.results ?? []).slice(0, 3);
  const collections = (collectionsQuery.data?.results ?? []).slice(0, 4);

  return (
    <div className="grid gap-6">
      <section className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-950">
        <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-xl font-semibold tracking-tight text-neutral-950 dark:text-white">
              {t('home.welcomeBack')}, {profile?.nickname || t('common.anonymous')}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500 dark:text-neutral-400">{t('home.feedBody')}</p>
          </div>
          {isAdmin ? <Badge variant="secondary">{t('auth.admin')}</Badge> : null}
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          {[
            { label: t('home.marked'), value: recentSubjectsQuery.data?.count ?? 0, href: routes.library },
            { label: t('status.doing'), value: watchingSubjectsQuery.data?.count ?? 0, href: routes.library },
            { label: t('common.reviews'), value: reviewsQuery.data?.count ?? 0, href: routes.reviews },
          ].map((item) => (
            <Link className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 transition hover:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-900/60" key={item.label} to={item.href}>
              <strong className="text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">{item.value}</strong>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{item.label}</p>
            </Link>
          ))}
        </div>
      </section>

      {isAdmin ? (
        <section className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-950">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-start gap-4">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]">
                <ShieldCheck className="size-5" />
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold uppercase text-[var(--color-accent-strong)]">{t('auth.admin')}</span>
                  <Badge variant="secondary">{t('admin.syncTitle')}</Badge>
                </div>
                <h2 className="mt-2 text-lg font-semibold tracking-tight text-neutral-950 dark:text-white">{t('home.adminTitle')}</h2>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-neutral-500 dark:text-neutral-400">{t('admin.description')}</p>
              </div>
            </div>
            <Link className="button button-secondary w-fit shrink-0" to={routes.admin}>
              <ShieldCheck className="size-4" />
              {t('nav.admin')}
            </Link>
          </div>
        </section>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <main className="grid min-w-0 content-start gap-6">
          <section className="grid gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-neutral-950 dark:text-white">{t('home.feed')}</h2>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{t('home.feedBody')}</p>
              </div>
              <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.communityPosts}>{t('home.viewAll')}</Link>
            </div>

            <div className="grid gap-3">
              {feedItems.map((activity) => (
                <div className="grid gap-3" key={activity.id}>
                  <CommunityContentCard
                    actions={(
                      <>
                        <CommunityTargetActions
                          reactionCount={typeof activity.reaction_count === 'number' ? activity.reaction_count : undefined}
                          reportLabel={t('community.reportActivity')}
                          targetId={activity.id}
                          targetType="activity"
                          viewerState={activity.viewer_state}
                        />
                        <button
                          className="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-sm font-semibold text-neutral-500 transition hover:bg-neutral-100 hover:text-[var(--color-accent-strong)] dark:text-neutral-400 dark:hover:bg-neutral-900"
                          type="button"
                          onClick={() => setExpandedActivityId((current) => current === activity.id ? null : activity.id)}
                        >
                          <MessageSquare className="size-4" />
                          {expandedActivityId === activity.id ? t('community.hideComments') : t('community.viewComments')}
                        </button>
                      </>
                    )}
                    author={activity.user?.id ? {
                      href: routes.userProfile(activity.user.id),
                      name: activity.user.nickname || t('common.anonymous'),
                      avatar: activity.user.avatar,
                    } : undefined}
                    body={activityBody(activity, t)}
                    cover={activity.subject?.image_thumbnail || null}
                    date={formatDate(activity.created_at)}
                    href={activityHref(activity)}
                    icon={<MessageSquare className="size-4" />}
                    subject={activity.subject?.id ? {
                      href: routes.subject(activity.subject.id),
                      title: activity.subject.display_title || activity.subject.title || activity.subject.title_cn || t('common.untitledSubject'),
                    } : undefined}
                    title={activityTitle(activity, t('common.untitled'))}
                    typeLabel={activityTypeLabel(activity.activity_type, t)}
                  />
                  {expandedActivityId === activity.id ? (
                    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-950">
                      <CommunityCommentsSection targetType="activity" targetId={activity.id} />
                    </div>
                  ) : null}
                </div>
              ))}
              {feedQuery.isLoading ? <LoadingState title={t('home.loadingFeed')} /> : null}
              {feedQuery.isError ? <ErrorState title={t('home.feedErrorTitle')} description={t('home.feedErrorBody')} /> : null}
              {!feedQuery.isLoading && !feedQuery.isError && feedItems.length === 0 ? (
                <EmptyState
                  title={t('home.feedEmptyTitle')}
                  description={t('home.feedEmptyBody')}
                  action={(
                    <Link className="button button-secondary h-9 rounded-full px-3" to={routes.communityPosts}>
                      {t('nav.posts')}
                    </Link>
                  )}
                />
              ) : null}
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <div className="grid content-start gap-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{t('home.recentMarks')}</h2>
                <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.library}>{t('home.viewLibrary')}</Link>
              </div>
              <div className="grid overflow-hidden rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
                {recentSubjects.map((item) => (
                  <Link className="grid grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-3 border-b border-neutral-200 px-3 py-3 transition last:border-b-0 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900/60" key={item.id} to={routes.subject(item.subject.id)}>
                    <img className="h-14 w-10 rounded-md bg-neutral-100 object-cover dark:bg-neutral-900" src={item.subject.image_thumbnail || item.subject.image || '/assets/placeholders/subject-cover.png'} alt="" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-neutral-950 dark:text-white">{subjectTitle(item, t('common.untitledSubject'))}</span>
                      <span className="mt-1 block text-xs text-neutral-500 dark:text-neutral-400">{formatDate(item.updated_at || item.created_at)}</span>
                    </span>
                    <Badge variant="secondary">{statusLabel(item.status, t)}</Badge>
                  </Link>
                ))}
                {recentSubjectsQuery.isError ? <ErrorState title={t('home.marksErrorTitle')} description={t('home.marksErrorBody')} /> : null}
                {!recentSubjectsQuery.isLoading && !recentSubjectsQuery.isError && recentSubjects.length === 0 ? <p className="p-5 text-sm text-neutral-500 dark:text-neutral-400">{t('home.noMarks')}</p> : null}
              </div>
            </div>

            <div className="grid content-start gap-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{t('home.latestReviews')}</h2>
                <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.reviews}>{t('home.viewAll')}</Link>
              </div>
              <div className="grid gap-3">
                {reviews.map((review) => (
                  <Link className="block rounded-lg border border-neutral-200 bg-white p-4 transition hover:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-950" key={review.id} to={routes.review(review.id)}>
                    <p className="line-clamp-1 text-sm font-semibold text-neutral-950 dark:text-white">{review.title}</p>
                    <p className="mt-1 line-clamp-2 text-sm leading-6 text-neutral-500 dark:text-neutral-400">{review.content || t('common.noContent')}</p>
                  </Link>
                ))}
                {reviewsQuery.isError ? <ErrorState title={t('reviews.errorTitle')} description={t('search.errorBody')} /> : null}
                {!reviewsQuery.isLoading && !reviewsQuery.isError && reviews.length === 0 ? <p className="rounded-lg border border-dashed border-neutral-200 bg-white p-5 text-sm text-neutral-500 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-400">{t('home.noReviews')}</p> : null}
              </div>
            </div>
          </section>
        </main>

        <aside className="grid content-start gap-4">
          <section className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-950">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{t('home.continue')}</h2>
              <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.library}>{t('home.viewLibrary')}</Link>
            </div>
            <div className="mt-4 grid gap-3">
              {watchingSubjects.map((item) => (
                <Link className="grid min-w-0 grid-cols-[44px_minmax(0,1fr)] gap-3" key={item.id} to={routes.subject(item.subject.id)}>
                  <img className="h-14 w-10 rounded-md bg-neutral-100 object-cover dark:bg-neutral-900" src={item.subject.image_thumbnail || item.subject.image || '/assets/placeholders/subject-cover.png'} alt="" />
                  <span className="grid min-w-0 content-center">
                    <span className="line-clamp-2 text-sm font-semibold leading-5 text-neutral-950 dark:text-white">{subjectTitle(item, t('common.untitledSubject'))}</span>
                    <span className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{item.rating ? `${item.rating} / 10` : statusLabel(item.status, t)}</span>
                  </span>
                </Link>
              ))}
              {watchingSubjectsQuery.isError ? <ErrorState title={t('home.marksErrorTitle')} description={t('home.marksErrorBody')} /> : null}
              {!watchingSubjectsQuery.isLoading && !watchingSubjectsQuery.isError && watchingSubjects.length === 0 ? <p className="text-sm text-neutral-500 dark:text-neutral-400">{t('home.noWatching')}</p> : null}
            </div>
          </section>

          <section className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-950">
            <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{t('home.quickActions')}</h2>
            <div className="mt-4 grid gap-2">
              <Link className="button button-secondary justify-start" to={routes.library}><Library className="size-4" /> {t('nav.library')}</Link>
              <Link className="button button-secondary justify-start" to={routes.calendar}><CalendarDays className="size-4" /> {t('nav.calendar')}</Link>
              <Link className="button button-secondary justify-start" to={routes.collections}><Layers3 className="size-4" /> {t('nav.collections')}</Link>
              {isAdmin ? <Link className="button button-secondary justify-start" to={routes.admin}><ShieldCheck className="size-4" /> {t('nav.admin')}</Link> : null}
              <Link className="button button-secondary justify-start" to={routes.settings}><Settings className="size-4" /> {t('settings.title')}</Link>
            </div>
          </section>

          <section className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-950">
            <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{t('nav.collections')}</h2>
            <div className="mt-4 grid gap-3">
              {collections.map((collection) => (
                <Link className="grid gap-1 rounded-lg px-2 py-1.5 transition hover:bg-neutral-50 dark:hover:bg-neutral-900" key={collection.id} to={routes.collections}>
                  <p className="line-clamp-1 text-sm font-semibold text-neutral-950 dark:text-white">{collection.name}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">{collection.item_count ?? 0} {t('common.items')}</p>
                </Link>
              ))}
              {collectionsQuery.isError ? <ErrorState title={t('collections.errorTitle')} description={t('search.errorBody')} /> : null}
              {!collectionsQuery.isLoading && !collectionsQuery.isError && collections.length === 0 ? <p className="text-sm text-neutral-500 dark:text-neutral-400">{t('home.noCollections')}</p> : null}
            </div>
          </section>
        </aside>
      </div>

    </div>
  );
}
