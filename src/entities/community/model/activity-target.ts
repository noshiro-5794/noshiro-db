import type { Activity } from '@/shared/api';
import { routes } from '@/shared/routing/paths';

function withHash(href: string, hash?: string | number | null) {
  if (!hash) return href;
  return `${href}#comment-${encodeURIComponent(String(hash))}`;
}

function collectionHref(activity: Activity, fallback: string, ownerId?: number | string) {
  if (!activity.collection?.id) return fallback;
  const resolvedOwnerId = ownerId ?? activity.user?.id;
  if (!resolvedOwnerId) return routes.collections;
  return routes.userCollection(resolvedOwnerId, activity.collection.id);
}

export function activityTargetHref(
  activity: Activity,
  fallback: string = routes.communityPosts,
  ownerId?: number | string,
) {
  const commentId = activity.comment?.id;

  if (activity.activity_type === 'comment_created') {
    if (activity.post?.id) return withHash(routes.communityPost(activity.post.id), commentId);
    if (activity.review?.id) return withHash(routes.review(activity.review.id), commentId);
    if (activity.collection?.id) return withHash(collectionHref(activity, routes.collections, ownerId), commentId);
  }

  if (activity.activity_type === 'post_created' && activity.post?.id) return routes.communityPost(activity.post.id);
  if (activity.activity_type === 'review_created' && activity.review?.id) return routes.review(activity.review.id);
  if (
    (activity.activity_type === 'collection_created' || activity.activity_type === 'collection_item_added') &&
    activity.collection?.id
  ) {
    return collectionHref(activity, fallback, ownerId);
  }
  if (
    (activity.activity_type === 'user_subject_created' || activity.activity_type === 'user_subject_updated') &&
    activity.subject?.id
  ) {
    return routes.entity(activity.subject.id);
  }
  if (activity.activity_type === 'user_followed' && activity.target_user?.id)
    return routes.userProfile(activity.target_user.id);

  if (activity.post?.id) return routes.communityPost(activity.post.id);
  if (activity.review?.id) return routes.review(activity.review.id);
  if (activity.collection?.id) return collectionHref(activity, fallback, ownerId);
  if (activity.subject?.id) return routes.entity(activity.subject.id);
  if (activity.target_user?.id) return routes.userProfile(activity.target_user.id);
  return fallback;
}
