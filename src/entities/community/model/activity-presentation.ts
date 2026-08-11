import type { Activity, SubjectSummary } from '@/shared/api';
import type { MessageKey } from '@/shared/i18n';

export function activitySubjectTitle(
  subject: Pick<SubjectSummary, 'display_title' | 'title' | 'title_cn'> | null | undefined,
  fallback: string,
) {
  return subject?.display_title || subject?.title || subject?.title_cn || fallback;
}

function firstMeaningfulLine(value?: string) {
  return value
    ?.split('\n')
    .find((line) => line.trim())
    ?.trim();
}

export function activityTitle(activity: Activity, fallback: string) {
  return (
    activitySubjectTitle(activity.subject, '') ||
    activity.review?.title ||
    activity.collection?.name ||
    activity.target_user?.nickname ||
    firstMeaningfulLine(activity.post?.content) ||
    firstMeaningfulLine(activity.comment?.content) ||
    fallback
  );
}

export function activityBody(activity: Activity, fallback: string) {
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

export function activityTypeLabel(type: string, t: (key: MessageKey) => string) {
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
