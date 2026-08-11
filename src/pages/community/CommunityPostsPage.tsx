import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { formatDate } from '@/shared/lib/date';
import { useMemo, useState, type ReactNode } from 'react';
import { getRouteApi, Link } from '@tanstack/react-router';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { Bell, Bookmark, User, UserPlus } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { communityActivitiesApi } from '@/entities/community';
import { ActivityTimelineItem, CreatePostDialog } from '@/features/community';
import { communityQueries, communityQueryKeys } from '@/entities/community';
import { getNextApiPageParam } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import type { CommunityPostsSearch } from '@/shared/routing/route-search';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu, type FilterMenuOption } from '@/shared/ui/FilterMenu';
import { Page } from '@/shared/ui/Page';
import { Toggle, ToggleGroup } from '@/shared/ui/Toggle';
import './community-posts.css';

const pageSize = 12;
const communityPostsRoute = getRouteApi('/community/posts');

type ActivityScope = 'following' | 'all' | 'mine';
type ActivityFilter = 'all' | NonNullable<CommunityPostsSearch['type']>;

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

export function CommunityPostsPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const navigate = communityPostsRoute.useNavigate();
  const search = communityPostsRoute.useSearch();
  const scope: ActivityScope = search.scope ?? 'following';
  const activityFilter: ActivityFilter = search.type ?? 'all';
  const commentsPage = search.activity_comments_page ?? 1;
  const [expandedActivityId, setExpandedActivityId] = useState<number | null>(null);

  const activityQuery = useInfiniteQuery({
    queryKey: [...communityQueryKeys.activities(), 'stream', scope, activityFilter, pageSize] as const,
    queryFn: ({ pageParam, signal }) => {
      const query = {
        page: pageParam,
        page_size: pageSize,
        ordering: '-created_at' as const,
        ...(activityFilter === 'all' ? {} : { activity_type: activityFilter }),
      };
      if (scope === 'all') return communityActivitiesApi.listPublic(query, { signal });
      if (scope === 'mine') return communityActivitiesApi.listMine(query, { signal });
      return communityActivitiesApi.listFeed({ ...query, include_self: true }, { signal });
    },
    initialPageParam: 1,
    getNextPageParam: getNextApiPageParam,
  });
  const followingQuery = useQuery(communityQueries.myFollowing({ page_size: 6 }));

  const activities = useMemo(
    () => activityQuery.data?.pages.flatMap((page) => page.results) ?? [],
    [activityQuery.data?.pages],
  );
  const scopeOptions: FilterMenuOption<ActivityScope>[] = [
    { label: t('community.scopeFollowing'), value: 'following' },
    { label: t('community.scopeAll'), value: 'all' },
    { label: t('community.scopeMine'), value: 'mine' },
  ];
  const activityOptions: FilterMenuOption<ActivityFilter>[] = getActivityFilterOptions(t);

  function updateScope(nextScope: ActivityScope) {
    setExpandedActivityId(null);
    void navigate({ search: (current) => ({ ...current, scope: nextScope === 'following' ? undefined : nextScope }) });
  }

  function updateActivityFilter(nextType: ActivityFilter) {
    setExpandedActivityId(null);
    void navigate({ search: (current) => ({ ...current, type: nextType === 'all' ? undefined : nextType }) });
  }

  function loadMore() {
    void activityQuery.fetchNextPage();
  }

  return (
    <Page title={t('community.hubTitle')} eyebrow={t('nav.groupCommunity')} actions={<CreatePostDialog />}>
      <div className="activity-hub-grid">
        <div className="activity-stream-column">
          <section className="activity-stream-frame">
            <section className="activity-feed-bar">
              <ToggleGroup
                aria-label={t('community.filterAllActivity')}
                className="activity-feed-tabs"
                variant="tab"
                value={[scope]}
                onValueChange={(values) => {
                  const nextScope = values[0];
                  if (nextScope) updateScope(nextScope);
                }}
              >
                {scopeOptions.map((option) => (
                  <Toggle key={option.value} value={option.value} variant="tab">
                    {option.label}
                  </Toggle>
                ))}
              </ToggleGroup>
              <div className="activity-feed-filter">
                <FilterMenu
                  label={t('community.activityType')}
                  options={activityOptions}
                  value={activityFilter}
                  onChange={updateActivityFilter}
                />
              </div>
            </section>

            <div className="activity-stream-content">
              {activityQuery.isLoading ? <LoadingState title={t('community.loadingFeed')} /> : null}
              {activityQuery.isError ? (
                <ErrorState title={t('community.feedErrorTitle')} description={t('community.feedErrorBody')} />
              ) : null}
              {!activityQuery.isLoading && !activityQuery.isError && activities.length === 0 ? (
                <EmptyState title={t('community.noFeedTitle')} description={t('community.noFeedBody')} />
              ) : null}
              {activities.length > 0 ? (
                <div className="activity-timeline-list">
                  {activities.map((activity) => (
                    <ActivityTimelineItem
                      activity={activity}
                      commentsPage={commentsPage}
                      isExpanded={expandedActivityId === activity.id}
                      key={activity.id}
                      onCommentsPageChange={(page) =>
                        void navigate({ search: (current) => ({ ...current, activity_comments_page: page }) })
                      }
                      onToggleComments={() => {
                        setExpandedActivityId((current) => (current === activity.id ? null : activity.id));
                      }}
                    />
                  ))}
                </div>
              ) : null}
            </div>

            {!activityQuery.isLoading && activities.length > 0 ? (
              <div className="activity-load-more">
                {activityQuery.hasNextPage ? (
                  <Button
                    disabled={activityQuery.isFetchingNextPage}
                    type="button"
                    variant="secondary"
                    onClick={loadMore}
                  >
                    {activityQuery.isFetchingNextPage ? t('community.loadingMore') : t('community.loadMore')}
                  </Button>
                ) : (
                  <span>{t('community.feedEnd')}</span>
                )}
              </div>
            ) : null}
          </section>
        </div>

        <aside className="activity-right-rail">
          <MiniPanel title={t('community.yourNetwork')} body={t('community.yourNetworkBody')}>
            <div className="community-user-list">
              {(followingQuery.data?.results ?? []).map((relation) => (
                <Link
                  className="community-user-row"
                  key={relation.user.id}
                  params={{ userId: String(relation.user.id) }}
                  to="/users/$userId"
                >
                  <span className="community-user-main">
                    <img
                      alt=""
                      decoding="async"
                      loading="lazy"
                      referrerPolicy="no-referrer"
                      src={relation.user.avatar || placeholderImagePaths.avatar}
                    />
                    <span>
                      <strong>{relation.user.nickname || t('common.anonymous')}</strong>
                      <small>{formatDate(relation.followed_at)}</small>
                    </span>
                  </span>
                </Link>
              ))}
              {followingQuery.isLoading ? (
                <p className="text-sm text-[var(--ui-text-muted)]">{t('common.loading')}</p>
              ) : null}
              {!followingQuery.isLoading && (followingQuery.data?.results ?? []).length === 0 ? (
                <p className="text-sm leading-6 text-[var(--ui-text-muted)]">{t('community.noNetworkYet')}</p>
              ) : null}
            </div>
            {auth.profile?.user_id ? (
              <div className="community-side-footer">
                <Button asChild className="w-full justify-center" size="sm" type="button" variant="secondary">
                  <Link params={{ userId: String(auth.profile.user_id) }} to="/users/$userId/following">
                    {t('community.viewAllFollowing')}
                  </Link>
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
                <Link
                  className="community-shortcut-link"
                  params={{ userId: String(auth.profile.user_id) }}
                  to="/users/$userId/following"
                >
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
