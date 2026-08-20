import { getRouteApi, Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, UserPlus } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { communityQueries } from '@/entities/community';
import { ActivityTimelineItem, useFollowUserMutation } from '@/features/community';
import { useI18n } from '@/shared/i18n';
import { UserSubjectListItem } from '@/entities/library';
import { PublicCollectionPackCard, PublicReviewItem } from '@/widgets/public-content';
import { publicUserQueries } from '@/entities/user';
import { routes } from '@/shared/routing/paths';
import { parseIntegerParam } from '@/shared/routing/search-params';
import { Avatar } from '@/shared/ui/Avatar';
import { Button } from '@/shared/ui/Button';
import { ListSurface, ResultsState, type ResultsStatus } from '@/shared/ui/DataView';
import { DetailSection } from '@/shared/ui/Detail';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

const publicUserRoute = getRouteApi('/users/$userId');

function resultsStatus(isLoading: boolean, isError: boolean, itemCount: number): ResultsStatus {
  if (isLoading) return 'loading';
  if (isError) return 'error';
  return itemCount === 0 ? 'empty' : 'ready';
}

export function PublicUserPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const params = publicUserRoute.useParams();
  const navigate = publicUserRoute.useNavigate();
  const { activity_comments_page: commentsPage = 1 } = publicUserRoute.useSearch();
  const [expandedActivityId, setExpandedActivityId] = useState<number | null>(null);
  const userId = parseIntegerParam(params.userId, { min: 1 }) ?? 0;
  const isValidUserId = userId > 0;
  const isSelf = auth.profile?.user_id === userId;

  const profileQuery = useQuery({ ...publicUserQueries.publicProfile(userId), enabled: isValidUserId });
  const activitiesQuery = useQuery({
    ...communityQueries.userActivities(userId, { page_size: 8, ordering: '-created_at' }),
    enabled: isValidUserId,
  });
  const reviewsQuery = useQuery({
    ...publicUserQueries.publicReviews(userId, { page_size: 3, ordering: '-created_at' }),
    enabled: isValidUserId,
  });
  const collectionsQuery = useQuery({
    ...publicUserQueries.publicCollections(userId, { page_size: 4, ordering: '-id' }),
    enabled: isValidUserId,
  });
  const subjectsQuery = useQuery({
    ...publicUserQueries.publicSubjects(userId, { page_size: 4, ordering: '-id' }),
    enabled: isValidUserId,
  });

  const followMutation = useFollowUserMutation();

  const profile = profileQuery.data;
  const activities = activitiesQuery.data?.results ?? [];
  const reviews = reviewsQuery.data?.results ?? [];
  const collections = collectionsQuery.data?.results ?? [];
  const subjects = subjectsQuery.data?.results ?? [];

  function toggleFollow() {
    if (!profile || followMutation.isPending) return;
    followMutation.mutate({ targetUserId: profile.id, shouldFollow: !profile.is_following });
  }

  if (!isValidUserId) {
    return (
      <Page title={t('profile.title')} eyebrow={t('profile.title')}>
        <ErrorState title={t('profile.invalidTitle')} description={t('profile.invalidBody')} />
      </Page>
    );
  }

  if (profileQuery.isLoading) {
    return (
      <Page title={t('profile.title')} eyebrow={t('profile.title')}>
        <LoadingState title={t('profile.loading')} />
      </Page>
    );
  }

  if (profileQuery.isError || !profile) {
    return (
      <Page title={t('profile.title')} eyebrow={t('profile.title')}>
        <ErrorState title={t('profile.errorTitle')} description={t('profile.errorBody')} />
      </Page>
    );
  }

  const profileTitleId = `profile-title-${profile.id}`;
  const reviewsStatus = resultsStatus(reviewsQuery.isLoading, reviewsQuery.isError, reviews.length);
  const subjectsStatus = resultsStatus(subjectsQuery.isLoading, subjectsQuery.isError, subjects.length);
  const collectionsStatus = resultsStatus(collectionsQuery.isLoading, collectionsQuery.isError, collections.length);
  const activitiesStatus = resultsStatus(activitiesQuery.isLoading, activitiesQuery.isError, activities.length);

  return (
    <Page
      actions={
        isSelf ? (
          <Button asChild type="button" variant="secondary">
            <Link to={routes.me}>{t('profile.viewOwnProfile')}</Link>
          </Button>
        ) : auth.isAuthenticated ? (
          <Button
            disabled={followMutation.isPending}
            type="button"
            variant={profile.is_following ? 'secondary' : 'default'}
            onClick={toggleFollow}
          >
            <UserPlus className="size-4" /> {profile.is_following ? t('profile.following') : t('profile.follow')}
          </Button>
        ) : (
          <Button asChild type="button" variant="secondary">
            <Link to={routes.login}>{t('profile.loginToFollow')}</Link>
          </Button>
        )
      }
      eyebrow={t('profile.title')}
      headerMode="context"
      seoDescription={profile.bio || undefined}
      title={profile.nickname || t('profile.title')}
    >
      <div className="grid min-w-0 gap-8 xl:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="min-w-0">
          <section
            aria-labelledby={profileTitleId}
            className="xl:sticky xl:top-[calc(var(--ui-sticky-content-top)+1.5rem)]"
          >
            <div className="flex min-w-0 items-center gap-4 xl:grid">
              <Avatar className="size-20 xl:size-24" loading="eager" src={profile.avatar} />
              <div className="min-w-0 xl:mt-1">
                <h1 className="m-0 truncate text-xl font-semibold leading-tight text-foreground" id={profileTitleId}>
                  {profile.nickname}
                </h1>
                <p className="mt-1 line-clamp-3 text-sm leading-6 text-muted-foreground xl:line-clamp-none">
                  {profile.bio || t('profile.noBio')}
                </p>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 rounded-sm bg-muted px-3 py-2.5">
              <Link
                className="grid min-w-0 gap-0.5 border-r border-border-subtle pr-3 transition-colors hover:text-[var(--ui-accent-text)]"
                params={{ userId: String(profile.id) }}
                to="/users/$userId/followers"
              >
                <strong className="text-base font-semibold tabular-nums text-foreground">
                  {profile.stats.follower_count}
                </strong>
                <span className="truncate text-xs text-muted-foreground">{t('profile.followers')}</span>
              </Link>
              <Link
                className="grid min-w-0 gap-0.5 pl-3 transition-colors hover:text-[var(--ui-accent-text)]"
                params={{ userId: String(profile.id) }}
                to="/users/$userId/following"
              >
                <strong className="text-base font-semibold tabular-nums text-foreground">
                  {profile.stats.following_count}
                </strong>
                <span className="truncate text-xs text-muted-foreground">{t('profile.followingCount')}</span>
              </Link>
            </div>
          </section>
        </aside>

        <div className="grid min-w-0 content-start gap-6">
          <DetailSection
            actions={
              <Link
                className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground transition-colors hover:text-[var(--ui-accent-text)]"
                params={{ userId: String(profile.id) }}
                to="/users/$userId/reviews"
              >
                {t('home.viewAll')} <ArrowRight className="size-4" />
              </Link>
            }
            className="border-t-0 pt-0"
            meta={`${reviewsQuery.data?.count ?? 0} ${t('common.items')}`}
            title={t('profile.latestReviews')}
            titleId="profile-latest-reviews"
          >
            <ResultsState
              emptyDescription={t('profile.noReviewsBody')}
              emptyTitle={t('profile.noReviewsTitle')}
              errorDescription={t('profile.contentErrorBody')}
              errorTitle={t('profile.contentErrorTitle')}
              loadingTitle={t('profile.loadingReviews')}
              status={reviewsStatus}
            >
              <div className="grid gap-3">
                {reviews.map((review) => (
                  <PublicReviewItem key={review.id} review={review} />
                ))}
              </div>
            </ResultsState>
          </DetailSection>

          <DetailSection
            actions={
              <Link
                className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground transition-colors hover:text-[var(--ui-accent-text)]"
                params={{ userId: String(profile.id) }}
                to="/users/$userId/entities"
              >
                {t('home.viewAll')} <ArrowRight className="size-4" />
              </Link>
            }
            meta={`${subjectsQuery.data?.count ?? 0} ${t('common.items')}`}
            title={t('profile.recentSubjects')}
            titleId="profile-recent-subjects"
          >
            <ResultsState
              emptyDescription={t('profile.noSubjectsBody')}
              emptyTitle={t('profile.noSubjectsTitle')}
              errorDescription={t('profile.contentErrorBody')}
              errorTitle={t('profile.contentErrorTitle')}
              loadingTitle={t('profile.loadingSubjects')}
              status={subjectsStatus}
            >
              <ListSurface>
                {subjects.map((item) => (
                  <UserSubjectListItem key={item.id} item={item} />
                ))}
              </ListSurface>
            </ResultsState>
          </DetailSection>

          <DetailSection
            actions={
              <Link
                className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground transition-colors hover:text-[var(--ui-accent-text)]"
                params={{ userId: String(profile.id) }}
                to="/users/$userId/collections"
              >
                {t('home.viewAll')} <ArrowRight className="size-4" />
              </Link>
            }
            meta={`${collectionsQuery.data?.count ?? 0} ${t('common.items')}`}
            title={t('profile.publicCollections')}
            titleId="profile-public-collections"
          >
            <ResultsState
              emptyDescription={t('profile.noCollectionsBody')}
              emptyTitle={t('profile.noCollectionsTitle')}
              errorDescription={t('profile.contentErrorBody')}
              errorTitle={t('profile.contentErrorTitle')}
              loadingTitle={t('profile.loadingCollections')}
              status={collectionsStatus}
            >
              <div className="grid auto-rows-fr gap-2 sm:grid-cols-2 xl:grid-cols-4">
                {collections.map((collection) => (
                  <PublicCollectionPackCard collection={collection} key={collection.id} userId={profile.id} />
                ))}
              </div>
            </ResultsState>
          </DetailSection>

          <DetailSection
            meta={`${activities.length} ${t('common.items')}`}
            title={t('profile.publicActivity')}
            titleId="profile-public-activity"
          >
            <ResultsState
              emptyDescription={t('profile.noActivityBody')}
              emptyTitle={t('profile.noActivityTitle')}
              errorDescription={t('profile.contentErrorBody')}
              errorTitle={t('profile.contentErrorTitle')}
              loadingTitle={t('profile.loadingActivity')}
              status={activitiesStatus}
            >
              <ListSurface>
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
              </ListSurface>
            </ResultsState>
          </DetailSection>
        </div>
      </div>
    </Page>
  );
}
