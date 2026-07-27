import { Link } from '@/shared/routing/navigation';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CalendarDays, Layers3, Library, MessageSquare, Settings, ShieldCheck } from 'lucide-react';
import { CalendarBoard } from './CalendarBoard';
import { activityTargetHref } from '@/entities/community';
import { CommunityCommentsSection } from '@/features/community';
import { CommunityContentCard } from '@/entities/community';
import { CommunityTargetActions } from '@/features/community';
import { communityQueries } from '@/entities/community';
import { SearchShowcase } from './SearchShowcase';
import { libraryQueries } from '@/entities/library';
import { subjectQueries } from '@/entities/subject';
import { useI18n } from '@/shared/i18n';
import type { Activity, CurrentUserProfile, UserSubject } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Badge } from '@/shared/ui/Badge';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';

const avatarPlaceholder = '/assets/placeholders/avatar.png';

export function SessionCheckingHome() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="h-44 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] sm:col-span-2" />
      <div className="h-44 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)]" />
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
          className="motion-rise inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-xs font-medium text-[var(--color-text-muted)] shadow-sm transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-accent-strong)]"
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
          <Link className="button button-primary h-10 rounded-full px-5" to={routes.search}>
            {t('public.searchAction')}
          </Link>
          <Link className="button button-secondary h-10 rounded-full px-5" to={routes.register}>
            {t('auth.register')}
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
    activity.subject?.display_title ||
    activity.subject?.title ||
    activity.review?.title ||
    activity.collection?.name ||
    activity.target_user?.nickname ||
    activity.post?.content?.split('\n').find(Boolean)?.slice(0, 96) ||
    activity.comment?.content?.split('\n').find(Boolean)?.slice(0, 96) ||
    fallback
  );
}

function activityBody(activity: Activity, t: ReturnType<typeof useI18n>['t']) {
  return (
    activity.message ||
    activity.post?.content ||
    activity.comment?.content ||
    activity.review?.content ||
    activity.collection?.note ||
    activity.target_user?.nickname ||
    activity.subject?.display_subtitle ||
    activity.subject?.platform ||
    t('common.noContent')
  );
}

export function UserHome({ isAdmin, profile }: UserHomeProps) {
  const { t } = useI18n();
  const [expandedActivityId, setExpandedActivityId] = useState<number | null>(null);
  const feedQuery = useQuery(communityQueries.feed({ page_size: 5, include_self: true, ordering: '-created_at' }));
  const recentSubjectsQuery = useQuery(libraryQueries.userSubjects({ page_size: 4, ordering: '-updated_at' }));
  const watchingSubjectsQuery = useQuery(
    libraryQueries.userSubjects({ status: 'doing', page_size: 3, ordering: '-updated_at' }),
  );
  const reviewsQuery = useQuery(libraryQueries.reviews({ page_size: 3, ordering: '-created_at' }));
  const collectionsQuery = useQuery(libraryQueries.collections({ page_size: 4, ordering: '-id' }));
  const recentSubjects = recentSubjectsQuery.data?.results ?? [];
  const feedItems = (feedQuery.data?.results ?? []).slice(0, 5);
  const watchingSubjects = watchingSubjectsQuery.data?.results ?? [];
  const reviews = (reviewsQuery.data?.results ?? []).slice(0, 3);
  const collections = (collectionsQuery.data?.results ?? []).slice(0, 4);

  return (
    <div className="home-shell">
      <section className="home-overview">
        <div className="home-overview-main">
          <div className="flex min-w-0 items-center gap-3.5">
            <img alt="" className="home-avatar" src={profile?.avatar || avatarPlaceholder} />
            <div className="min-w-0">
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <p className="home-kicker">{t('home.welcomeBack')}</p>
                {isAdmin ? <Badge variant="secondary">{t('auth.admin')}</Badge> : null}
              </div>
              <h2 className="home-overview-title">{profile?.nickname || t('common.anonymous')}</h2>
            </div>
          </div>
        </div>
        <div className="home-stat-grid">
          {[
            { label: t('home.marked'), value: recentSubjectsQuery.data?.count ?? 0, href: routes.library },
            { label: t('status.doing'), value: watchingSubjectsQuery.data?.count ?? 0, href: routes.library },
            { label: t('common.reviews'), value: reviewsQuery.data?.count ?? 0, href: routes.reviews },
          ].map((item) => (
            <Link className="home-stat" key={item.label} to={item.href}>
              <strong>{item.value}</strong>
              <span>{item.label}</span>
            </Link>
          ))}
        </div>
      </section>

      {isAdmin ? (
        <section className="home-admin-panel">
          <div className="home-admin-content">
            <span className="home-panel-icon">
              <ShieldCheck className="size-5" />
            </span>
            <div className="min-w-0">
              <p className="home-admin-meta">
                {t('auth.admin')}
                <span aria-hidden="true">/</span>
                {t('admin.syncTitle')}
              </p>
              <h2 className="home-admin-title">{t('home.adminTitle')}</h2>
            </div>
          </div>
          <Link className="button button-secondary home-admin-action" to={routes.admin}>
            <ShieldCheck className="size-4" />
            {t('nav.admin')}
          </Link>
        </section>
      ) : null}

      <div className="home-layout">
        <main className="home-main">
          <section className="home-panel home-feed-panel">
            <div className="home-section-header">
              <h2>{t('home.feed')}</h2>
              <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.communityPosts}>
                {t('home.viewAll')}
              </Link>
            </div>

            <div className="home-feed-list">
              {feedItems.map((activity) => (
                <div className="grid gap-3" key={activity.id}>
                  <CommunityContentCard
                    actions={
                      <>
                        <CommunityTargetActions
                          inlineMiddleAction={
                            <button
                              aria-label={
                                expandedActivityId === activity.id
                                  ? t('community.hideComments')
                                  : t('community.viewComments')
                              }
                              className={`timeline-action-button ${expandedActivityId === activity.id ? 'is-active' : ''}`}
                              type="button"
                              onClick={() =>
                                setExpandedActivityId((current) => (current === activity.id ? null : activity.id))
                              }
                            >
                              <MessageSquare className="size-4" />
                              {typeof activity.reply_count === 'number' ? <span>{activity.reply_count}</span> : null}
                            </button>
                          }
                          presentation="inline"
                          reactionCount={
                            typeof activity.reaction_count === 'number' ? activity.reaction_count : undefined
                          }
                          reportLabel={t('community.reportActivity')}
                          targetId={activity.id}
                          targetType="activity"
                          viewerState={activity.viewer_state}
                        />
                      </>
                    }
                    author={
                      activity.user?.id
                        ? {
                            href: routes.userProfile(activity.user.id),
                            name: activity.user.nickname || t('common.anonymous'),
                            avatar: activity.user.avatar,
                          }
                        : undefined
                    }
                    body={activityBody(activity, t)}
                    cover={activity.subject?.image_thumbnail || null}
                    date={formatDate(activity.created_at)}
                    href={activityTargetHref(activity, routes.home)}
                    icon={<MessageSquare className="size-4" />}
                    subject={
                      activity.subject?.id
                        ? {
                            href: routes.subject(activity.subject.id),
                            title:
                              activity.subject.display_title ||
                              activity.subject.title ||
                              activity.subject.title_cn ||
                              t('common.untitledSubject'),
                          }
                        : undefined
                    }
                    title={activityTitle(activity, t('common.untitled'))}
                    typeLabel={activityTypeLabel(activity.activity_type, t)}
                  />
                  {expandedActivityId === activity.id ? (
                    <div className="activity-comments-drawer">
                      <CommunityCommentsSection targetType="activity" targetId={activity.id} />
                    </div>
                  ) : null}
                </div>
              ))}
              {feedQuery.isLoading ? <LoadingState title={t('home.loadingFeed')} /> : null}
              {feedQuery.isError ? (
                <ErrorState title={t('home.feedErrorTitle')} description={t('home.feedErrorBody')} />
              ) : null}
              {!feedQuery.isLoading && !feedQuery.isError && feedItems.length === 0 ? (
                <EmptyState
                  title={t('home.feedEmptyTitle')}
                  description={t('home.feedEmptyBody')}
                  action={
                    <Link className="button button-secondary h-9 rounded-full px-3" to={routes.communityPosts}>
                      {t('nav.posts')}
                    </Link>
                  }
                />
              ) : null}
            </div>
          </section>

          <section className="home-card-grid">
            <div className="home-panel">
              <div className="home-section-header">
                <h2>{t('home.recentMarks')}</h2>
                <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.library}>
                  {t('home.viewLibrary')}
                </Link>
              </div>
              <div className="home-list">
                {recentSubjects.map((item) => (
                  <Link className="home-list-item is-mark" key={item.id} to={routes.subject(item.subject.id)}>
                    <img
                      src={
                        item.subject.image_thumbnail || item.subject.image || '/assets/placeholders/subject-cover.png'
                      }
                      alt=""
                    />
                    <span className="min-w-0">
                      <span className="home-list-title">{subjectTitle(item, t('common.untitledSubject'))}</span>
                      <span className="home-list-meta">{formatDate(item.updated_at || item.created_at)}</span>
                    </span>
                    <Badge variant="secondary">{statusLabel(item.status, t)}</Badge>
                  </Link>
                ))}
                {recentSubjectsQuery.isError ? (
                  <ErrorState title={t('home.marksErrorTitle')} description={t('home.marksErrorBody')} />
                ) : null}
                {!recentSubjectsQuery.isLoading && !recentSubjectsQuery.isError && recentSubjects.length === 0 ? (
                  <p className="home-empty-line">{t('home.noMarks')}</p>
                ) : null}
              </div>
            </div>

            <div className="home-panel">
              <div className="home-section-header">
                <h2>{t('home.latestReviews')}</h2>
                <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.reviews}>
                  {t('home.viewAll')}
                </Link>
              </div>
              <div className="home-list">
                {reviews.map((review) => (
                  <Link className="home-review-row" key={review.id} to={routes.review(review.id)}>
                    <p>{review.title}</p>
                    <span>{review.content || t('common.noContent')}</span>
                  </Link>
                ))}
                {reviewsQuery.isError ? (
                  <ErrorState title={t('reviews.errorTitle')} description={t('search.errorBody')} />
                ) : null}
                {!reviewsQuery.isLoading && !reviewsQuery.isError && reviews.length === 0 ? (
                  <p className="home-empty-line">{t('home.noReviews')}</p>
                ) : null}
              </div>
            </div>
          </section>
        </main>

        <aside className="home-rail">
          <section className="home-panel">
            <div className="home-section-header">
              <h2>{t('home.continue')}</h2>
              <Link className="text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.library}>
                {t('home.viewLibrary')}
              </Link>
            </div>
            <div className="home-list is-compact">
              {watchingSubjects.map((item) => (
                <Link className="home-list-item" key={item.id} to={routes.subject(item.subject.id)}>
                  <img
                    src={item.subject.image_thumbnail || item.subject.image || '/assets/placeholders/subject-cover.png'}
                    alt=""
                  />
                  <span className="grid min-w-0 content-center">
                    <span className="home-list-title">{subjectTitle(item, t('common.untitledSubject'))}</span>
                    <span className="home-list-meta">
                      {item.rating ? `${item.rating} / 10` : statusLabel(item.status, t)}
                    </span>
                  </span>
                </Link>
              ))}
              {watchingSubjectsQuery.isError ? (
                <ErrorState title={t('home.marksErrorTitle')} description={t('home.marksErrorBody')} />
              ) : null}
              {!watchingSubjectsQuery.isLoading && !watchingSubjectsQuery.isError && watchingSubjects.length === 0 ? (
                <p className="home-empty-line">{t('home.noWatching')}</p>
              ) : null}
            </div>
          </section>

          <section className="home-panel">
            <div className="home-section-header">
              <h2>{t('home.quickActions')}</h2>
            </div>
            <div className="home-shortcut-grid">
              {[
                { label: t('nav.library'), href: routes.library, icon: <Library className="size-4" /> },
                { label: t('nav.calendar'), href: routes.calendar, icon: <CalendarDays className="size-4" /> },
                { label: t('nav.collections'), href: routes.collections, icon: <Layers3 className="size-4" /> },
                ...(isAdmin
                  ? [{ label: t('nav.admin'), href: routes.admin, icon: <ShieldCheck className="size-4" /> }]
                  : []),
                { label: t('settings.title'), href: routes.settings, icon: <Settings className="size-4" /> },
              ].map((item) => (
                <Link className="home-shortcut" key={item.href} to={item.href}>
                  <span className="inline-flex items-center gap-2">
                    {item.icon}
                    {item.label}
                  </span>
                </Link>
              ))}
            </div>
          </section>

          <section className="home-panel">
            <div className="home-section-header">
              <h2>{t('nav.collections')}</h2>
            </div>
            <div className="home-list is-compact">
              {collections.map((collection) => (
                <Link className="home-collection-row" key={collection.id} to={routes.collections}>
                  <p>{collection.name}</p>
                  <span>
                    {collection.item_count ?? 0} {t('common.items')}
                  </span>
                </Link>
              ))}
              {collectionsQuery.isError ? (
                <ErrorState title={t('collections.errorTitle')} description={t('search.errorBody')} />
              ) : null}
              {!collectionsQuery.isLoading && !collectionsQuery.isError && collections.length === 0 ? (
                <p className="home-empty-line">{t('home.noCollections')}</p>
              ) : null}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
