import { Link, useParams } from 'react-router-dom';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, FileText, Library, MessageSquare, UserPlus, Users } from 'lucide-react';
import { useAuth } from '@/features/auth/use-auth';
import { invalidateCommunityFollows } from '@/features/community/cache';
import { CommunityCommentsSection } from '@/features/community/components/CommunityCommentsSection';
import { CommunityContentCard } from '@/features/community/components/CommunityContentCard';
import { CommunityTargetActions } from '@/features/community/components/CommunityTargetActions';
import { useI18n } from '@/features/i18n/use-i18n';
import { socialMutations, socialQueries, socialQueryKeys } from '@/features/social/social-queries';
import type { Activity, Collection, Review, UserSubject } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';

const avatarPlaceholder = '/assets/placeholders/avatar.png';
const coverPlaceholder = '/assets/placeholders/subject-cover.png';

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function activityHref(activity: Activity, ownerId?: number) {
  if (activity.post?.id) return routes.communityPost(activity.post.id);
  if (activity.review?.id) return routes.review(activity.review.id);
  if (activity.collection?.id && ownerId) return routes.userCollection(ownerId, activity.collection.id);
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

function activityBody(activity: Activity, fallback: string) {
  return (
    activity.message
    || activity.post?.content
    || activity.comment?.content
    || activity.review?.content
    || activity.collection?.note
    || activity.target_user?.nickname
    || activity.subject?.display_subtitle
    || activity.subject?.platform
    || fallback
  );
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

function reviewSubjectTitle(review: Review, fallback: string) {
  return review.subject?.display_title || review.subject?.title || review.subject?.title_cn || fallback;
}

function CollectionCard({ collection, userId }: { collection: Collection; userId: number }) {
  const { t } = useI18n();

  return (
    <CommunityContentCard
      badges={<Badge variant="secondary">{collection.item_count ?? 0} {t('common.items')}</Badge>}
      body={collection.note || t('common.noNote')}
      href={routes.userCollection(userId, collection.id)}
      icon={<BookOpen className="size-4" />}
      title={collection.name}
      typeLabel={t('community.targetType.collection')}
    />
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

  const profileQuery = useQuery({ ...socialQueries.publicProfile(userId), enabled: isValidUserId });
  const activitiesQuery = useQuery({ ...socialQueries.publicActivities(userId, { page_size: 8, ordering: '-created_at' }), enabled: isValidUserId });
  const reviewsQuery = useQuery({ ...socialQueries.publicReviews(userId, { page_size: 3, ordering: '-created_at' }), enabled: isValidUserId });
  const collectionsQuery = useQuery({ ...socialQueries.publicCollections(userId, { page_size: 4, ordering: '-id' }), enabled: isValidUserId });
  const subjectsQuery = useQuery({ ...socialQueries.publicSubjects(userId, { page_size: 4, ordering: '-updated_at' }), enabled: isValidUserId });

  const invalidateProfile = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: socialQueryKeys.publicProfile(userId) }),
      queryClient.invalidateQueries({ queryKey: socialQueryKeys.publicFollowers(userId) }),
      queryClient.invalidateQueries({ queryKey: socialQueryKeys.myFollowing() }),
      queryClient.invalidateQueries({ queryKey: socialQueryKeys.feed() }),
      invalidateCommunityFollows(queryClient, userId),
    ]);
  };

  const followMutation = useMutation({ ...socialMutations.follow(), onSuccess: invalidateProfile });
  const unfollowMutation = useMutation({ ...socialMutations.unfollow(), onSuccess: invalidateProfile });

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

  if (!isValidUserId) {
    return (
      <Page title={t('profile.title')} description={t('profile.invalidBody')}>
        <ErrorState title={t('profile.invalidTitle')} description={t('profile.invalidBody')} />
      </Page>
    );
  }

  return (
    <Page
      title={profile?.nickname || t('profile.title')}
      eyebrow={t('profile.eyebrow')}
      description={profile?.bio || t('profile.description')}
      actions={profile ? (
        isSelf ? (
          <Button asChild type="button" variant="secondary">
            <Link to={routes.me}>{t('profile.viewOwnProfile')}</Link>
          </Button>
        ) : auth.isAuthenticated ? (
          <Button disabled={followMutation.isPending || unfollowMutation.isPending} type="button" variant={profile.is_following ? 'secondary' : 'default'} onClick={toggleFollow}>
            <UserPlus className="size-4" /> {profile.is_following ? t('profile.following') : t('profile.follow')}
          </Button>
        ) : (
          <Button asChild type="button" variant="secondary">
            <Link to={routes.login}>{t('profile.loginToFollow')}</Link>
          </Button>
        )
      ) : null}
    >
      {profileQuery.isLoading ? <LoadingState title={t('profile.loading')} /> : null}
      {profileQuery.isError ? <ErrorState title={t('profile.errorTitle')} description={t('profile.errorBody')} /> : null}
      {profile ? (
        <div className="grid gap-8 xl:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="grid content-start gap-5">
            <section className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-950">
              <img className="size-24 rounded-full bg-neutral-100 object-cover dark:bg-neutral-900" src={profile.avatar || avatarPlaceholder} alt="" />
              <h2 className="mt-4 text-xl font-semibold tracking-tight text-neutral-950 dark:text-white">{profile.nickname}</h2>
              <p className="mt-2 text-sm leading-6 text-neutral-500 dark:text-neutral-400">{profile.bio || t('profile.noBio')}</p>
              <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
                <Link className="rounded-lg p-1 transition hover:bg-neutral-50 dark:hover:bg-neutral-900" to={routes.userSubjects(profile.id)}>
                  <strong className="text-lg text-neutral-950 dark:text-white">{profile.stats.subject_count}</strong>
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{t('common.subjects')}</p>
                </Link>
                <Link className="rounded-lg p-1 transition hover:bg-neutral-50 dark:hover:bg-neutral-900" to={routes.userReviews(profile.id)}>
                  <strong className="text-lg text-neutral-950 dark:text-white">{profile.stats.review_count}</strong>
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{t('common.reviews')}</p>
                </Link>
                <Link className="rounded-lg p-1 transition hover:bg-neutral-50 dark:hover:bg-neutral-900" to={routes.userCollections(profile.id)}>
                  <strong className="text-lg text-neutral-950 dark:text-white">{profile.stats.collection_count}</strong>
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{t('nav.collections')}</p>
                </Link>
                <Link className="rounded-lg p-1 transition hover:bg-neutral-50 dark:hover:bg-neutral-900" to={routes.userFollowers(profile.id)}>
                  <strong className="text-lg text-neutral-950 dark:text-white">{profile.stats.follower_count}</strong>
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{t('profile.followers')}</p>
                </Link>
              </div>
              <Link className="mt-4 flex items-center gap-2 rounded-lg text-sm text-neutral-500 transition hover:text-[var(--color-accent-strong)] dark:text-neutral-400" to={routes.userFollowing(profile.id)}>
                <Users className="size-4" />
                {profile.stats.following_count} {t('profile.followingCount')}
              </Link>
            </section>
          </aside>

          <main className="grid min-w-0 content-start gap-6">
            <section className="grid gap-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{t('profile.latestReviews')}</h2>
                <Link className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.userReviews(profile.id)}>
                  {t('home.viewAll')} <FileText className="size-4" />
                </Link>
              </div>
              {reviewsQuery.isLoading ? <LoadingState title={t('profile.loadingReviews')} /> : null}
              {reviewsQuery.isError ? <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} /> : null}
              {!reviewsQuery.isLoading && !reviewsQuery.isError && reviews.length === 0 ? (
                <EmptyState title={t('profile.noReviewsTitle')} description={t('profile.noReviewsBody')} />
              ) : null}
              <div className="grid gap-3">
                {reviews.map((review) => (
                  <CommunityContentCard
                    badges={review.is_spoiler ? <Badge>{t('common.spoiler')}</Badge> : null}
                    body={review.content || t('common.noContent')}
                    cover={review.subject?.image_thumbnail || review.subject?.image || coverPlaceholder}
                    date={formatDate(review.updated_at || review.created_at)}
                    href={routes.review(review.id)}
                    isSpoiler={review.is_spoiler}
                    key={review.id}
                    subject={review.subject ? {
                      href: routes.subject(review.subject.id),
                      title: reviewSubjectTitle(review, t('common.untitledSubject')),
                    } : undefined}
                    title={review.title || t('common.untitled')}
                    typeLabel={t('community.targetType.review')}
                  />
                ))}
              </div>
            </section>

            <section className="grid gap-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{t('profile.publicActivity')}</h2>
                <MessageSquare className="size-4 text-neutral-400" />
              </div>
              {activitiesQuery.isLoading ? <LoadingState title={t('profile.loadingActivity')} /> : null}
              {activitiesQuery.isError ? <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} /> : null}
              {!activitiesQuery.isLoading && !activitiesQuery.isError && activities.length === 0 ? (
                <EmptyState title={t('profile.noActivityTitle')} description={t('profile.noActivityBody')} />
              ) : null}
              <div className="grid gap-3">
                {activities.map((activity) => (
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
                      body={activityBody(activity, t('common.noContent'))}
                      cover={activity.subject?.image_thumbnail || null}
                      date={formatDate(activity.created_at)}
                      href={activityHref(activity, profile.id)}
                      icon={<MessageSquare className="size-4" />}
                      subject={activity.subject?.id ? {
                        href: routes.subject(activity.subject.id),
                        title: activity.subject.display_title || activity.subject.title || activity.subject.title_cn || t('common.untitledSubject'),
                      } : undefined}
                      title={activityTitle(activity, t('common.untitled'))}
                      typeLabel={activityTypeLabel(activity.activity_type, t)}
                    />
                      {expandedActivityId === activity.id ? (
                        <div className="mt-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-950">
                          <CommunityCommentsSection targetType="activity" targetId={activity.id} />
                        </div>
                      ) : null}
                  </div>
                ))}
              </div>
            </section>

            <section className="grid gap-3 md:grid-cols-2">
              <div className="grid content-start gap-3">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{t('profile.recentSubjects')}</h2>
                  <Link className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.userSubjects(profile.id)}>
                    {t('home.viewAll')} <Library className="size-4" />
                  </Link>
                </div>
                {subjectsQuery.isLoading ? <LoadingState title={t('profile.loadingSubjects')} /> : null}
                {subjectsQuery.isError ? <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} /> : null}
                {!subjectsQuery.isLoading && !subjectsQuery.isError && subjects.length === 0 ? (
                  <EmptyState title={t('profile.noSubjectsTitle')} description={t('profile.noSubjectsBody')} />
                ) : null}
                <div className="grid gap-3">
                  {subjects.map((item) => (
                    <CommunityContentCard
                      badges={<Badge variant="secondary">{statusLabel(item.status, t)}</Badge>}
                      body={item.comment || item.subject.display_subtitle || item.subject.platform || ''}
                      cover={item.subject.image_thumbnail || item.subject.image || coverPlaceholder}
                      date={formatDate(item.updated_at || item.created_at)}
                      href={routes.subject(item.subject.id)}
                      key={item.id}
                      title={subjectTitle(item, t('common.untitledSubject'))}
                      typeLabel={item.subject.subject_type}
                    />
                  ))}
                </div>
              </div>

              <div className="grid content-start gap-3">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="font-semibold tracking-tight text-neutral-950 dark:text-white">{t('profile.publicCollections')}</h2>
                  <Link className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--color-accent-strong)]" to={routes.userCollections(profile.id)}>
                    {t('home.viewAll')} <BookOpen className="size-4" />
                  </Link>
                </div>
                {collectionsQuery.isLoading ? <LoadingState title={t('profile.loadingCollections')} /> : null}
                {collectionsQuery.isError ? <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} /> : null}
                {!collectionsQuery.isLoading && !collectionsQuery.isError && collections.length === 0 ? (
                  <EmptyState title={t('profile.noCollectionsTitle')} description={t('profile.noCollectionsBody')} />
                ) : null}
                <div className="grid gap-3">
                  {collections.map((collection) => <CollectionCard collection={collection} key={collection.id} userId={profile.id} />)}
                </div>
              </div>
            </section>
          </main>
        </div>
      ) : null}
    </Page>
  );
}
