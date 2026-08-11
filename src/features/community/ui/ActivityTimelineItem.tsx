import { Bookmark, Library, MessageSquare, Star, UserPlus } from 'lucide-react';
import {
  activityBody,
  activitySubjectTitle,
  activityTargetHref,
  activityTitle,
  activityTypeLabel,
} from '@/entities/community';
import type { Activity } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { formatDate } from '@/shared/lib/date';
import { Link } from '@tanstack/react-router';
import { routes } from '@/shared/routing/paths';
import { Avatar } from '@/shared/ui/Avatar';
import { SpoilerText } from '@/shared/ui/SpoilerText';
import { Toggle } from '@/shared/ui/Toggle';
import { CommunityCommentsSection } from './CommunityCommentsSection';
import { CommunityTargetActions } from './CommunityTargetActions';
import './activity-timeline.css';

function activityIcon(type: string) {
  if (type === 'review_created') return <Star className="size-4" />;
  if (type === 'collection_created' || type === 'collection_item_added') return <Library className="size-4" />;
  if (type === 'user_followed') return <UserPlus className="size-4" />;
  if (type === 'user_subject_created' || type === 'user_subject_updated') return <Bookmark className="size-4" />;
  return <MessageSquare className="size-4" />;
}

export function ActivityTimelineItem({
  activity,
  commentsPage,
  isExpanded,
  onCommentsPageChange,
  onToggleComments,
}: {
  activity: Activity;
  commentsPage: number;
  isExpanded: boolean;
  onCommentsPageChange: (page: number) => void;
  onToggleComments: () => void;
}) {
  const { t } = useI18n();
  const author = activity.user;
  const targetSubject = activity.subject || activity.post?.subject || null;
  const cover = activity.subject?.image_thumbnail || activity.post?.subject?.image_thumbnail || null;
  const href = activityTargetHref(activity, routes.communityPosts);
  const body = activity.activity_type === 'user_followed' ? '' : activityBody(activity, t('common.noContent'));
  const commentCount = typeof activity['reply_count'] === 'number' ? activity['reply_count'] : undefined;

  return (
    <article className="activity-timeline-item">
      <div className="activity-timeline-body">
        <header className="activity-timeline-header">
          {author?.id ? (
            <Link className="activity-avatar-link" to={routes.userProfile(author.id)}>
              <Avatar alt={author.nickname || t('common.anonymous')} className="activity-avatar" src={author.avatar} />
            </Link>
          ) : (
            <Avatar className="activity-avatar" />
          )}

          <div className="activity-timeline-heading">
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
            </div>

            <Link className="activity-title-link" to={href}>
              {activityTitle(activity, t('common.untitled'))}
            </Link>
          </div>

          <span className="activity-type-icon">{activityIcon(activity.activity_type)}</span>
        </header>

        <div className="activity-timeline-content">
          {body ? (
            <SpoilerText
              className="activity-body-copy"
              isSpoiler={Boolean(activity.post?.is_spoiler || activity.review?.is_spoiler)}
              revealLabel={t('common.revealSpoiler')}
            >
              {body}
            </SpoilerText>
          ) : null}

          {targetSubject?.id ? (
            <Link className="activity-subject-preview" to={routes.subject(targetSubject.id)}>
              {cover ? (
                <img alt="" decoding="async" loading="lazy" referrerPolicy="no-referrer" src={cover} />
              ) : (
                <span />
              )}
              <span className="activity-subject-copy">
                <span>{activitySubjectTitle(targetSubject, t('common.untitledSubject'))}</span>
                <small>
                  {'display_subtitle' in targetSubject &&
                  typeof targetSubject.display_subtitle === 'string' &&
                  targetSubject.display_subtitle
                    ? targetSubject.display_subtitle
                    : String(targetSubject.subject_type || '')}
                </small>
              </span>
            </Link>
          ) : null}

          <div className="activity-actions">
            <CommunityTargetActions
              inlineMiddleAction={
                <Toggle
                  aria-label={isExpanded ? t('community.hideComments') : t('community.viewComments')}
                  className="timeline-action-button"
                  pressed={isExpanded}
                  variant="bare"
                  onPressedChange={onToggleComments}
                >
                  <MessageSquare className="size-4" />
                  {typeof commentCount === 'number' ? <span>{commentCount}</span> : null}
                </Toggle>
              }
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
              <CommunityCommentsSection
                currentPage={commentsPage}
                targetType="activity"
                targetId={activity.id}
                onPageChange={onCommentsPageChange}
              />
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}
