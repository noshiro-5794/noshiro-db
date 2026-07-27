import { Link, useParams } from '@/shared/routing/navigation';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, FileText, Library, MessageSquare, UserPlus, Users } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { activityTargetHref } from '@/entities/community';
import { communityMutations, communityQueries } from '@/entities/community';
import { invalidateCommunityFollows } from '@/features/community';
import { CommunityCommentsSection } from '@/features/community';
import { CommunityContentCard } from '@/entities/community';
import { CommunityTargetActions } from '@/features/community';
import { useI18n } from '@/shared/i18n';
import { PublicCollectionPackCard, PublicReviewItem, PublicSubjectListItem } from '@/widgets/public-content';
import { publicUserQueries } from '@/entities/user';
import type { Activity } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

const avatarPlaceholder = '/assets/placeholders/avatar.png';

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
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

function activityBody(activity: Activity, fallback: string) {
  return (
    activity.message ||
    activity.post?.content ||
    activity.comment?.content ||
    activity.review?.content ||
    activity.collection?.note ||
    activity.target_user?.nickname ||
    activity.subject?.display_subtitle ||
    activity.subject?.platform ||
    fallback
  );
}

export function PublicUserPage() {
  const { t } = useI18n();
  const auth = useAuth();
  const queryClient = useQueryClient();
  const params = useParams();
  const [expandedActivityId, setExpandedActivityId] = useState<number | null>(null);
  const userId = Number(params.userId);
  const isValidUserId = Number.isFinite(userId) && userId > 0;
  const isSelf = auth.profile?.user_id ? Number(auth.profile.user_id) === userId : false;

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
    ...publicUserQueries.publicSubjects(userId, { page_size: 4, ordering: '-updated_at' }),
    enabled: isValidUserId,
  });

  const invalidateProfile = async () => {
    await invalidateCommunityFollows(queryClient, userId);
  };

  const followMutation = useMutation({ ...communityMutations.follow(), onSuccess: invalidateProfile });
  const unfollowMutation = useMutation({ ...communityMutations.unfollow(), onSuccess: invalidateProfile });

  const profile = profileQuery.data;
  const activities = activitiesQuery.data?.results ?? [];
  const reviews = reviewsQuery.data?.results ?? [];
  const collections = collectionsQuery.data?.results ?? [];
  const subjects = subjectsQuery.data?.results ?? [];

  function toggleFollow() {
    if (!profile) return;
    if (profile.is_following) {
      unfollowMutation.mutate(profile.id);
    } else {
      followMutation.mutate(profile.id);
    }
  }

  function renderActivitySection(ownerId: number) {
    return (
      <section className="grid gap-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">
            {t('profile.publicActivity')}
          </h2>
          <MessageSquare className="size-4 text-neutral-400" />
        </div>
        {activitiesQuery.isLoading ? <LoadingState title={t('profile.loadingActivity')} /> : null}
        {activitiesQuery.isError ? (
          <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} />
        ) : null}
        {!activitiesQuery.isLoading && !activitiesQuery.isError && activities.length === 0 ? (
          <EmptyState title={t('profile.noActivityTitle')} description={t('profile.noActivityBody')} />
        ) : null}
        <div className="grid gap-3">
          {activities.map((activity) => (
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
                      reactionCount={typeof activity.reaction_count === 'number' ? activity.reaction_count : undefined}
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
                body={activityBody(activity, t('common.noContent'))}
                cover={activity.subject?.image_thumbnail || null}
                date={formatDate(activity.created_at)}
                href={activityTargetHref(activity, routes.home, ownerId)}
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
        </div>
      </section>
    );
  }

  if (!isValidUserId) {
    return (
      <Page title={t('profile.title')} eyebrow={t('profile.title')}>
        <ErrorState title={t('profile.invalidTitle')} description={t('profile.invalidBody')} />
      </Page>
    );
  }

  return (
    <Page
      title={profile?.nickname || t('profile.title')}
      eyebrow={t('profile.title')}
      description={profile?.bio || undefined}
      actions={
        profile ? (
          isSelf ? (
            <Button asChild type="button" variant="secondary">
              <Link to={routes.me}>{t('profile.viewOwnProfile')}</Link>
            </Button>
          ) : auth.isAuthenticated ? (
            <Button
              disabled={followMutation.isPending || unfollowMutation.isPending}
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
        ) : null
      }
    >
      {profileQuery.isLoading ? <LoadingState title={t('profile.loading')} /> : null}
      {profileQuery.isError ? (
        <ErrorState title={t('profile.errorTitle')} description={t('profile.errorBody')} />
      ) : null}
      {profile ? (
        <div className="grid gap-8 xl:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="grid content-start gap-5">
            <section className="xl:sticky xl:top-6">
              <div className="flex items-center gap-4 xl:block">
                <img
                  className="size-20 rounded-full bg-[var(--color-surface-muted)] object-cover ring-1 ring-[var(--color-border)] xl:size-24"
                  src={profile.avatar || avatarPlaceholder}
                  alt=""
                />
                <div className="min-w-0 xl:mt-4">
                  <h2 className="truncate text-xl font-semibold tracking-tight text-neutral-950 dark:text-white">
                    {profile.nickname}
                  </h2>
                  <p className="mt-1 line-clamp-3 text-sm leading-6 text-neutral-500 dark:text-neutral-400 xl:line-clamp-none">
                    {profile.bio || t('profile.noBio')}
                  </p>
                </div>
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                <Link
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm text-[var(--color-text-muted)] shadow-sm transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-accent-strong)]"
                  to={routes.userFollowers(profile.id)}
                >
                  <Users className="size-4" />
                  <strong className="font-semibold text-[var(--color-text)]">{profile.stats.follower_count}</strong>
                  <span>{t('profile.followers')}</span>
                </Link>
                <Link
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm text-[var(--color-text-muted)] shadow-sm transition hover:border-[var(--color-accent-border)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-accent-strong)]"
                  to={routes.userFollowing(profile.id)}
                >
                  <Users className="size-4" />
                  <strong className="font-semibold text-[var(--color-text)]">{profile.stats.following_count}</strong>
                  <span>{t('profile.followingCount')}</span>
                </Link>
              </div>
            </section>
          </aside>

          <main className="grid min-w-0 content-start gap-6">
            <section className="grid gap-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">
                  {t('profile.latestReviews')}
                </h2>
                <Link
                  className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--color-accent-strong)]"
                  to={routes.userReviews(profile.id)}
                >
                  {t('home.viewAll')} <FileText className="size-4" />
                </Link>
              </div>
              {reviewsQuery.isLoading ? <LoadingState title={t('profile.loadingReviews')} /> : null}
              {reviewsQuery.isError ? (
                <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} />
              ) : null}
              {!reviewsQuery.isLoading && !reviewsQuery.isError && reviews.length === 0 ? (
                <EmptyState title={t('profile.noReviewsTitle')} description={t('profile.noReviewsBody')} />
              ) : null}
              <div className="grid gap-3">
                {reviews.map((review) => (
                  <PublicReviewItem key={review.id} review={review} />
                ))}
              </div>
            </section>

            <section className="grid gap-6">
              <div className="grid content-start gap-3">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">
                    {t('profile.recentSubjects')}
                  </h2>
                  <Link
                    className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--color-accent-strong)]"
                    to={routes.userSubjects(profile.id)}
                  >
                    {t('home.viewAll')} <Library className="size-4" />
                  </Link>
                </div>
                {subjectsQuery.isLoading ? <LoadingState title={t('profile.loadingSubjects')} /> : null}
                {subjectsQuery.isError ? (
                  <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} />
                ) : null}
                {!subjectsQuery.isLoading && !subjectsQuery.isError && subjects.length === 0 ? (
                  <EmptyState title={t('profile.noSubjectsTitle')} description={t('profile.noSubjectsBody')} />
                ) : null}
                <div className="content-list-panel">
                  {subjects.map((item) => (
                    <PublicSubjectListItem key={item.id} item={item} />
                  ))}
                </div>
              </div>

              <div className="grid content-start gap-3">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">
                    {t('profile.publicCollections')}
                  </h2>
                  <Link
                    className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--color-accent-strong)]"
                    to={routes.userCollections(profile.id)}
                  >
                    {t('home.viewAll')} <BookOpen className="size-4" />
                  </Link>
                </div>
                {collectionsQuery.isLoading ? <LoadingState title={t('profile.loadingCollections')} /> : null}
                {collectionsQuery.isError ? (
                  <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} />
                ) : null}
                {!collectionsQuery.isLoading && !collectionsQuery.isError && collections.length === 0 ? (
                  <EmptyState title={t('profile.noCollectionsTitle')} description={t('profile.noCollectionsBody')} />
                ) : null}
                <div className="grid auto-rows-fr gap-2 sm:grid-cols-2 xl:grid-cols-4">
                  {collections.map((collection) => (
                    <PublicCollectionPackCard collection={collection} key={collection.id} userId={profile.id} />
                  ))}
                </div>
              </div>
            </section>

            {renderActivitySection(profile.id)}
          </main>
        </div>
      ) : null}
    </Page>
  );
}
