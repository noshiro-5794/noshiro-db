import type { CommunityNotification } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import type { I18nState } from '@/shared/i18n';

type Translate = I18nState['t'];

function metadataNumber(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function withHash(href: string, hash?: string | null) {
  return hash ? `${href}#${hash}` : href;
}

export function notificationHref(notification: CommunityNotification) {
  const target = notification.target;
  if (!target) {
    const actorId = metadataNumber(notification.metadata, 'actor_id') ?? notification.actor?.id;
    return notification.notification_type === 'followed' && actorId ? routes.userProfile(actorId) : null;
  }

  if (target.type === 'post') return routes.communityPost(target.id);
  if (target.type === 'review') return routes.review(target.id);
  if (target.type === 'collection') {
    return target.owner?.id ? routes.userCollection(target.owner.id, target.id) : routes.collections;
  }
  if (target.type === 'activity') {
    if (target.post?.id) return routes.communityPost(target.post.id);
    if (target.review?.id) return routes.review(target.review.id);
    if (target.collection?.id)
      return target.collection.owner?.id
        ? routes.userCollection(target.collection.owner.id, target.collection.id)
        : routes.collections;
    if (target.comment?.id)
      return withHash(
        target.user?.id ? routes.userProfile(target.user.id) : routes.home,
        `comment-${target.comment.id}`,
      );
    if (target.subject?.id) return routes.subject(target.subject.id);
    if (target.target_user?.id) return routes.userProfile(target.target_user.id);
    if (target.user?.id) return routes.userProfile(target.user.id);
    return routes.home;
  }
  if (target.type === 'comment') {
    const commentHash = `comment-${target.id}`;
    if (target.post?.id) return withHash(routes.communityPost(target.post.id), commentHash);
    if (target.review?.id) return withHash(routes.review(target.review.id), commentHash);
    if (target.collection?.id && target.collection.owner?.id) {
      return withHash(routes.userCollection(target.collection.owner.id, target.collection.id), commentHash);
    }
    if (target.activity?.user?.id) return withHash(routes.userProfile(target.activity.user.id), commentHash);
    const postId = metadataNumber(notification.metadata, 'post_id');
    const reviewId = metadataNumber(notification.metadata, 'review_id');
    const collectionId = metadataNumber(notification.metadata, 'collection_id');
    if (postId) return withHash(routes.communityPost(postId), commentHash);
    if (reviewId) return withHash(routes.review(reviewId), commentHash);
    if (collectionId) return routes.collections;
    return routes.communityPosts;
  }

  if (target.post?.id) return routes.communityPost(target.post.id);
  if (target.review?.id) return routes.review(target.review.id);
  if (target.collection?.id)
    return target.collection.owner?.id
      ? routes.userCollection(target.collection.owner.id, target.collection.id)
      : routes.collections;
  if (target.subject?.id) return routes.subject(target.subject.id);
  if (target.user?.id) return routes.userProfile(target.user.id);
  if (target.target_user?.id) return routes.userProfile(target.target_user.id);

  return null;
}

function notificationTypeLabel(t: Translate, type: string) {
  if (type === 'followed') return t('community.notificationType.followed');
  if (type === 'commented') return t('community.notificationType.commented');
  if (type === 'reacted') return t('community.notificationType.reacted');
  if (type === 'mentioned') return t('community.notificationType.mentioned');
  return type.replaceAll('_', ' ');
}

function targetTypeLabel(t: Translate, notification: CommunityNotification) {
  const targetType = notification.target?.type;
  if (!targetType) return t('community.notificationTarget.content');
  if (targetType === 'post') return t('community.targetType.post');
  if (targetType === 'review') return t('community.targetType.review');
  if (targetType === 'collection') return t('community.targetType.collection');
  if (targetType === 'comment') return t('community.targetType.comment');
  if (targetType === 'activity') return t('community.targetType.activity');
  return targetType.replaceAll('_', ' ');
}

export function notificationMessage(t: Translate, notification: CommunityNotification) {
  const target = targetTypeLabel(t, notification);
  if (notification.notification_type === 'followed') return t('community.notificationMessage.followed');
  if (notification.notification_type === 'commented')
    return `${t('community.notificationMessage.commented')} ${target}`;
  if (notification.notification_type === 'reacted') return `${t('community.notificationMessage.reacted')} ${target}`;
  if (notification.notification_type === 'mentioned')
    return `${t('community.notificationMessage.mentioned')} ${target}`;
  return notificationTypeLabel(t, notification.notification_type);
}
