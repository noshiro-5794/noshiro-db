import { formatDateTime as formatDate } from '@/shared/lib/date';
import { Flag, Heart, MessageSquare, PencilLine, ShieldAlert, Trash2 } from 'lucide-react';
import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import type { CommunityCommentSummary } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Avatar } from '@/shared/ui/Avatar';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { SpoilerText } from '@/shared/ui/SpoilerText';
import { Toggle } from '@/shared/ui/Toggle';
import type { CommentNode } from '../model/comment-tree';
import './community-actions.css';

type CommentActions = {
  onDelete: (comment: CommunityCommentSummary) => void;
  onEdit: (comment: CommunityCommentSummary) => void;
  onLike: (comment: CommunityCommentSummary) => void;
  onReport: (comment: CommunityCommentSummary) => void;
  onReply: (comment: CommunityCommentSummary) => void;
};

type CommentThreadProps = CommentActions & {
  node: CommentNode;
  canInteract: boolean;
  canReply: boolean;
  currentUserId?: string | number | undefined;
  pending: boolean;
};

function CommentItem({
  comment,
  canInteract,
  canEdit,
  canReply,
  pending,
  onDelete,
  onEdit,
  onLike,
  onReport,
  onReply,
}: CommentActions & {
  comment: CommunityCommentSummary;
  canInteract: boolean;
  canEdit: boolean;
  canReply: boolean;
  pending: boolean;
}) {
  const { t } = useI18n();
  const isDeleted = Boolean(comment.is_hidden);

  return (
    <article className="timeline-comment-item scroll-mt-24" id={`comment-${comment.id}`}>
      {comment.author?.id && !isDeleted ? (
        <Link to={routes.userProfile(comment.author.id)}>
          <Avatar
            alt={comment.author.nickname || t('common.anonymous')}
            className="timeline-comment-avatar"
            src={comment.author.avatar}
          />
        </Link>
      ) : (
        <Avatar className="timeline-comment-avatar" />
      )}
      <div className="min-w-0">
        <div className="timeline-comment-meta">
          {comment.author?.id && !isDeleted ? (
            <Link className="timeline-comment-author" to={routes.userProfile(comment.author.id)}>
              {comment.author.nickname || t('common.anonymous')}
            </Link>
          ) : (
            <span className="timeline-comment-author">
              {isDeleted ? t('community.deletedComment') : t('common.anonymous')}
            </span>
          )}
          <span>{formatDate(comment.created_at)}</span>
          {comment.is_locked ? <Badge>{t('community.locked')}</Badge> : null}
          {comment.is_spoiler ? (
            <Badge>
              <ShieldAlert className="mr-1 size-3" /> {t('common.spoiler')}
            </Badge>
          ) : null}
        </div>
        <SpoilerText
          className={`timeline-comment-copy ${isDeleted ? 'is-deleted' : ''}`}
          isSpoiler={comment.is_spoiler && !isDeleted}
          revealLabel={t('common.revealSpoiler')}
        >
          {isDeleted ? t('community.deletedCommentBody') : comment.content}
        </SpoilerText>
        {canInteract && !isDeleted ? (
          <div className="timeline-comment-actions">
            <Toggle
              aria-label={t('community.like')}
              className="timeline-action-button"
              disabled={pending}
              pressed={Boolean(comment.viewer_state?.has_liked)}
              variant="bare"
              onPressedChange={() => {
                onLike(comment);
              }}
            >
              <Heart className="size-4" /> {comment.reaction_count ?? 0}
            </Toggle>
            {canReply ? (
              <Button
                aria-label={t('community.reply')}
                className="timeline-action-button"
                disabled={pending}
                size="sm"
                type="button"
                variant="unstyled"
                onClick={() => {
                  onReply(comment);
                }}
              >
                <MessageSquare className="size-4" />
              </Button>
            ) : null}
            <Button
              aria-label={t('community.report')}
              className="timeline-action-button"
              size="sm"
              type="button"
              variant="unstyled"
              onClick={() => {
                onReport(comment);
              }}
            >
              <Flag className="size-4" />
            </Button>
            {canEdit ? (
              <>
                <Button
                  aria-label={t('common.edit')}
                  className="timeline-action-button"
                  disabled={pending}
                  size="sm"
                  type="button"
                  variant="unstyled"
                  onClick={() => {
                    onEdit(comment);
                  }}
                >
                  <PencilLine className="size-4" />
                </Button>
                <Button
                  aria-label={t('common.delete')}
                  className="timeline-action-button"
                  disabled={pending}
                  size="sm"
                  type="button"
                  variant="unstyled"
                  onClick={() => {
                    onDelete(comment);
                  }}
                >
                  <Trash2 className="size-4" />
                </Button>
              </>
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}

export function CommentThread({
  node,
  canInteract,
  canReply,
  currentUserId,
  pending,
  onDelete,
  onEdit,
  onLike,
  onReport,
  onReply,
}: CommentThreadProps) {
  const isOwnComment = Boolean(node.author?.id && currentUserId && String(node.author.id) === String(currentUserId));
  const actions = { onDelete, onEdit, onLike, onReport, onReply };

  return (
    <div className="timeline-comment-thread">
      <CommentItem
        {...actions}
        comment={node}
        canEdit={isOwnComment && !node.is_hidden && !node.is_locked}
        canInteract={canInteract}
        canReply={canReply && !node.is_hidden && !node.is_locked}
        pending={pending}
      />
      {node.children.length > 0 ? (
        <div className="timeline-comment-children">
          {node.children.map((child) => (
            <CommentThread
              {...actions}
              key={child.id}
              node={child}
              canInteract={canInteract}
              canReply={canReply}
              currentUserId={currentUserId}
              pending={pending}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
