import { FormEvent, ReactNode, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell, Bookmark, Library, MessageSquare, Star, User, UserPlus } from 'lucide-react';
import { useAuth } from '@/features/auth/use-auth';
import { activityTargetHref } from '@/features/community/activity-target';
import { communityActivitiesApi } from '@/features/community/api';
import { invalidateCommunityTargets } from '@/features/community/cache';
import { CommunityCommentsSection } from '@/features/community/components/CommunityCommentsSection';
import { CommunityTargetActions } from '@/features/community/components/CommunityTargetActions';
import { communityMutations, communityQueries, communityQueryKeys } from '@/features/community/community-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import type { Activity, ActivityType, SubjectSummary } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu, type FilterMenuOption } from '@/shared/ui/FilterMenu';
import { Page } from '@/shared/ui/Page';

const pageSize = 12;

type ActivityScope = 'following' | 'all' | 'mine';
type ActivityFilter = 'all' | ActivityType;

function getNextPage(lastPage: { next: string | null }, pages: unknown[]) {
  return lastPage.next ? pages.length + 1 : undefined;
}

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function subjectTitle(subject: Pick<SubjectSummary, 'display_title' | 'title' | 'title_cn'> | null | undefined, fallback: string) {
  return subject?.display_title || subject?.title || subject?.title_cn || fallback;
}

function firstLine(value?: string, fallback = '') {
  return value?.split('\n').find((line) => line.trim())?.trim() || fallback;
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

function activityIcon(type: string) {
  if (type === 'review_created') return <Star className="size-4" />;
  if (type === 'collection_created' || type === 'collection_item_added') return <Library className="size-4" />;
  if (type === 'user_followed') return <UserPlus className="size-4" />;
  if (type === 'user_subject_created' || type === 'user_subject_updated') return <Bookmark className="size-4" />;
  return <MessageSquare className="size-4" />;
}

function activityTitle(activity: Activity, fallback: string) {
  return (
    subjectTitle(activity.subject, '')
    || activity.review?.title
    || activity.collection?.name
    || activity.target_user?.nickname
    || firstLine(activity.post?.content)
    || firstLine(activity.comment?.content)
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
    || activity.subject?.display_subtitle
    || activity.target_user?.nickname
    || t('common.noContent')
  );
}

function MiniPanel({ title, body, children }: { title: string; body?: string; children: ReactNode }) {
  return (
    <section className="community-side-panel">
      <div>
        <h2 className="community-side-title">{title}</h2>
        {body ? <p className="community-side-body">{body}</p> : null}
      </div>
      {children}
    </section>
  );
}

function ActivityTimelineItem({
  activity,
  isExpanded,
  onToggleComments,
}: {
  activity: Activity;
  isExpanded: boolean;
  onToggleComments: () => void;
}) {
  const { t } = useI18n();
  const author = activity.user;
  const targetSubject = activity.subject || activity.post?.subject || null;
  const cover = activity.subject?.image_thumbnail || activity.post?.subject?.image_thumbnail || null;
  const href = activityTargetHref(activity, routes.communityPosts);
  const body = activity.activity_type === 'user_followed' ? '' : activityBody(activity, t);
  const commentCount = typeof activity.reply_count === 'number' ? activity.reply_count : undefined;

  return (
    <article className="activity-timeline-item">
      <div className="activity-timeline-avatar">
        {author?.id ? (
          <Link to={routes.userProfile(author.id)}>
            <img
              className="activity-avatar"
              src={author.avatar || '/assets/placeholders/avatar.png'}
              alt=""
            />
          </Link>
        ) : (
          <img className="activity-avatar" src="/assets/placeholders/avatar.png" alt="" />
        )}
      </div>

      <div className="activity-timeline-body">
        <div className="activity-timeline-meta">
          {author?.id ? (
            <Link className="activity-author-link" to={routes.userProfile(author.id)}>
              {author.nickname || t('common.anonymous')}
            </Link>
          ) : (
            <span className="activity-author-link">{t('common.anonymous')}</span>
          )}
          <span>·</span>
          <span>{activityTypeLabel(activity.activity_type, t)}</span>
          <span>·</span>
          <span>{formatDate(activity.created_at)}</span>
          <span className="activity-type-icon">{activityIcon(activity.activity_type)}</span>
        </div>

        <Link className="activity-title-link" to={href}>
          {activityTitle(activity, t('common.untitled'))}
        </Link>

        {body ? (
          <p className={`activity-body-copy ${activity.post?.is_spoiler || activity.review?.is_spoiler ? 'is-spoiler' : ''}`}>
            {body}
          </p>
        ) : null}

        {targetSubject?.id ? (
          <Link className="activity-subject-preview" to={routes.subject(targetSubject.id)}>
            {cover ? (
              <img src={cover} alt="" />
            ) : (
              <span />
            )}
            <span className="activity-subject-copy">
              <span>{subjectTitle(targetSubject, t('common.untitledSubject'))}</span>
              <small>
                {'display_subtitle' in targetSubject && typeof targetSubject.display_subtitle === 'string' && targetSubject.display_subtitle ? targetSubject.display_subtitle : String(targetSubject.subject_type || '')}
              </small>
            </span>
          </Link>
        ) : null}

        <div className="activity-actions">
          <CommunityTargetActions
            inlineMiddleAction={(
              <button
                aria-label={isExpanded ? t('community.hideComments') : t('community.viewComments')}
                className={`timeline-action-button ${isExpanded ? 'is-active' : ''}`}
                type="button"
                onClick={onToggleComments}
              >
                <MessageSquare className="size-4" />
                {typeof commentCount === 'number' ? <span>{commentCount}</span> : null}
              </button>
            )}
            presentation="inline"
            reactionCount={typeof activity.reaction_count === 'number' ? activity.reaction_count : undefined}
            reportLabel={t('community.reportActivity')}
            targetId={activity.id}
            targetType="activity"
            viewerState={activity.viewer_state}
          />
        </div>

        {isExpanded ? (
          <div className="activity-comments-drawer">
            <CommunityCommentsSection targetType="activity" targetId={activity.id} />
          </div>
        ) : null}
      </div>
    </article>
  );
}

export function CommunityPostsPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const scope = parseScope(searchParams.get('scope'));
  const activityFilter = parseActivityFilter(searchParams.get('type'));
  const [expandedActivityId, setExpandedActivityId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [content, setContent] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [visibility, setVisibility] = useState<'public' | 'followers' | 'private'>('public');
  const [isSpoiler, setIsSpoiler] = useState(false);
  const [isNsfw, setIsNsfw] = useState(false);

  const activityQuery = useInfiniteQuery({
    queryKey: [...communityQueryKeys.activities(), 'stream', scope, activityFilter, pageSize] as const,
    queryFn: ({ pageParam }) => {
      const query = {
        page: pageParam,
        page_size: pageSize,
        ordering: '-created_at' as const,
        ...(activityFilter === 'all' ? {} : { activity_type: activityFilter }),
      };
      if (scope === 'all') return communityActivitiesApi.listPublic(query);
      if (scope === 'mine') return communityActivitiesApi.listMine(query);
      return communityActivitiesApi.listFeed({ ...query, include_self: true });
    },
    initialPageParam: 1,
    getNextPageParam: getNextPage,
  });
  const followingQuery = useQuery(communityQueries.myFollowing({ page_size: 6 }));

  const createPostMutation = useMutation({
    ...communityMutations.createPost(),
    onSuccess: async () => {
      setCreateOpen(false);
      setContent('');
      setSubjectId('');
      setVisibility('public');
      setIsSpoiler(false);
      setIsNsfw(false);
      await invalidateCommunityTargets(queryClient);
    },
  });
  const activities = useMemo(() => activityQuery.data?.pages.flatMap((page) => page.results) ?? [], [activityQuery.data?.pages]);
  const scopeOptions: FilterMenuOption<ActivityScope>[] = [
    { label: t('community.scopeFollowing'), value: 'following' },
    { label: t('community.scopeAll'), value: 'all' },
    { label: t('community.scopeMine'), value: 'mine' },
  ];
  const activityOptions: FilterMenuOption<ActivityFilter>[] = getActivityFilterOptions(t);

  function updateScope(nextScope: ActivityScope) {
    const next = new URLSearchParams(searchParams);
    if (nextScope === 'following') next.delete('scope');
    else next.set('scope', nextScope);
    setExpandedActivityId(null);
    setSearchParams(next);
  }

  function updateActivityFilter(nextType: ActivityFilter) {
    const next = new URLSearchParams(searchParams);
    if (nextType === 'all') next.delete('type');
    else next.set('type', nextType);
    setExpandedActivityId(null);
    setSearchParams(next);
  }

  function submitPost(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!content.trim()) return;
    createPostMutation.mutate({
      content,
      subject_id: subjectId.trim() || undefined,
      visibility,
      is_spoiler: isSpoiler,
      is_nsfw: isNsfw,
    });
  }

  function loadMore() {
    void activityQuery.fetchNextPage();
  }

  return (
    <Page
      title={t('community.hubTitle')}
      eyebrow={t('nav.groupCommunity')}
      actions={(
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button className="activity-new-post-button" type="button"><MessageSquare className="size-4" /> {t('community.newPost')}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{t('community.createPostTitle')}</DialogTitle>
              <DialogDescription>{t('community.createPostDescription')}</DialogDescription>
            </DialogHeader>
            <form className="grid gap-4" onSubmit={submitPost}>
              <textarea
                className="min-h-36 resize-y rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-sm leading-6 text-[var(--color-text)] outline-none transition placeholder:text-neutral-400 focus:border-[var(--color-accent-border)]"
                value={content}
                placeholder={t('community.postPlaceholder')}
                onChange={(event) => setContent(event.target.value)}
              />
              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px]">
                <label className="grid gap-1.5 text-sm">
                  <span className="font-semibold text-[var(--color-text)]">{t('community.attachSubjectId')}</span>
                  <input
                    className="h-10 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 text-[var(--color-text)] outline-none transition placeholder:text-neutral-400 focus:border-[var(--color-accent-border)]"
                    value={subjectId}
                    placeholder="00000000-0000-0000-0000-000000000000"
                    onChange={(event) => setSubjectId(event.target.value)}
                  />
                </label>
                <div className="grid gap-1.5 text-sm">
                  <span className="font-semibold text-[var(--color-text)]">{t('community.visibility')}</span>
                  <div className="grid grid-cols-3 gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-1">
                    {[
                      ['public', t('common.public')],
                      ['followers', t('community.followersVisibility')],
                      ['private', t('common.private')],
                    ].map(([value, label]) => (
                      <button
                        className={[
                          'h-8 rounded-md px-2 text-xs font-semibold transition',
                          visibility === value
                            ? 'bg-[var(--color-surface-elevated)] text-[var(--color-text)] shadow-sm'
                            : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]',
                        ].join(' ')}
                        key={value}
                        type="button"
                        onClick={() => setVisibility(value as 'public' | 'followers' | 'private')}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-3 text-sm text-neutral-500 dark:text-neutral-400">
                <label className="inline-flex items-center gap-2">
                  <input checked={isSpoiler} className="size-4 accent-[var(--color-accent)]" type="checkbox" onChange={(event) => setIsSpoiler(event.target.checked)} />
                  {t('community.markSpoiler')}
                </label>
                <label className="inline-flex items-center gap-2">
                  <input checked={isNsfw} className="size-4 accent-[var(--color-accent)]" type="checkbox" onChange={(event) => setIsNsfw(event.target.checked)} />
                  NSFW
                </label>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>{t('common.cancel')}</Button>
                <Button disabled={createPostMutation.isPending || !content.trim()} type="submit">
                  <MessageSquare className="size-4" /> {t('community.publishPost')}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      )}
    >
      <div className="community-hub-grid activity-hub-grid">
        <main className="activity-stream-column">
          <section className="activity-stream-frame">
            <section className="activity-feed-bar">
              <div className="activity-feed-tabs">
                {scopeOptions.map((option) => (
                  <button
                    className={scope === option.value ? 'is-active' : ''}
                    key={option.value}
                    type="button"
                    onClick={() => updateScope(option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <div className="activity-feed-filter">
                <FilterMenu label={t('community.activityType')} options={activityOptions} value={activityFilter} onChange={updateActivityFilter} />
              </div>
            </section>

            <div className="activity-stream-content">
              {activityQuery.isLoading ? <LoadingState title={t('community.loadingFeed')} /> : null}
              {activityQuery.isError ? <ErrorState title={t('community.feedErrorTitle')} description={t('community.feedErrorBody')} /> : null}
              {!activityQuery.isLoading && !activityQuery.isError && activities.length === 0 ? (
                <EmptyState title={t('community.noFeedTitle')} description={t('community.noFeedBody')} />
              ) : null}
              {activities.length > 0 ? (
                <div className="activity-timeline-list">
                  {activities.map((activity) => (
                    <ActivityTimelineItem
                      activity={activity}
                      isExpanded={expandedActivityId === activity.id}
                      key={activity.id}
                      onToggleComments={() => setExpandedActivityId((current) => current === activity.id ? null : activity.id)}
                    />
                  ))}
                </div>
              ) : null}
            </div>

            {!activityQuery.isLoading && activities.length > 0 ? (
              <div className="community-load-more">
                {activityQuery.hasNextPage ? (
                  <Button disabled={activityQuery.isFetchingNextPage} type="button" variant="secondary" onClick={loadMore}>
                    {activityQuery.isFetchingNextPage ? t('community.loadingMore') : t('community.loadMore')}
                  </Button>
                ) : (
                  <span>{t('community.feedEnd')}</span>
                )}
              </div>
            ) : null}
          </section>
        </main>

        <aside className="community-hub-sidebar activity-right-rail">
          <MiniPanel title={t('community.yourNetwork')} body={t('community.yourNetworkBody')}>
            <div className="community-user-list">
              {(followingQuery.data?.results ?? []).map((relation) => (
                <Link className="community-user-row" key={relation.user.id} to={routes.userProfile(relation.user.id)}>
                  <span className="community-user-main">
                    <img src={relation.user.avatar || '/assets/placeholders/avatar.png'} alt="" />
                    <span>
                      <strong>{relation.user.nickname || t('common.anonymous')}</strong>
                      <small>{formatDate(relation.followed_at)}</small>
                    </span>
                  </span>
                </Link>
              ))}
              {followingQuery.isLoading ? <p className="text-sm text-neutral-500 dark:text-neutral-400">{t('common.loading')}</p> : null}
              {!followingQuery.isLoading && (followingQuery.data?.results ?? []).length === 0 ? (
                <p className="text-sm leading-6 text-neutral-500 dark:text-neutral-400">{t('community.noNetworkYet')}</p>
              ) : null}
            </div>
            {auth.profile?.user_id ? (
              <div className="community-side-footer">
                <Button asChild className="w-full justify-center" size="sm" type="button" variant="secondary">
                  <Link to={routes.userFollowing(auth.profile.user_id)}>{t('community.viewAllFollowing')}</Link>
                </Button>
              </div>
            ) : null}
          </MiniPanel>

          <MiniPanel title={t('community.relatedSpaces')} body={t('community.relatedSpacesBody')}>
            <div className="community-shortcut-list">
              <Link className="community-shortcut-link" to={routes.me}>
                <User className="size-4" />
                <span>{t('profile.viewOwnProfile')}</span>
              </Link>
              {auth.profile?.user_id ? (
                <Link className="community-shortcut-link" to={routes.userFollowing(auth.profile.user_id)}>
                  <UserPlus className="size-4" />
                  <span>{t('profile.followingTitle')}</span>
                </Link>
              ) : null}
              <Link className="community-shortcut-link" to={routes.notifications}>
                <Bell className="size-4" />
                <span>{t('nav.notifications')}</span>
              </Link>
              <Link className="community-shortcut-link" to={routes.bookmarks}>
                <Bookmark className="size-4" />
                <span>{t('nav.bookmarks')}</span>
              </Link>
            </div>
          </MiniPanel>
        </aside>
      </div>
    </Page>
  );
}

function parseScope(value: string | null): ActivityScope {
  if (value === 'all' || value === 'mine') return value;
  return 'following';
}

function parseActivityFilter(value: string | null): ActivityFilter {
  if (
    value === 'post_created'
    || value === 'user_subject_created'
    || value === 'user_subject_updated'
    || value === 'review_created'
    || value === 'collection_created'
    || value === 'collection_item_added'
    || value === 'comment_created'
    || value === 'user_followed'
  ) {
    return value;
  }
  return 'all';
}

function getActivityFilterOptions(t: ReturnType<typeof useI18n>['t']): FilterMenuOption<ActivityFilter>[] {
  return [
    { label: t('community.filterAllActivity'), value: 'all' },
    { label: t('community.filterPosts'), value: 'post_created' },
    { label: t('community.filterMarks'), value: 'user_subject_created' },
    { label: t('community.filterMarkUpdates'), value: 'user_subject_updated' },
    { label: t('community.filterReviews'), value: 'review_created' },
    { label: t('community.filterCollections'), value: 'collection_created' },
    { label: t('community.filterCollectionItems'), value: 'collection_item_added' },
    { label: t('community.filterComments'), value: 'comment_created' },
    { label: t('community.filterFollows'), value: 'user_followed' },
  ];
}
