import { type ReactNode, useState } from 'react';
import { Link } from '@tanstack/react-router';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Bookmark, Flag, Heart } from 'lucide-react';
import { communityMutations } from '@/entities/community';
import { useAuth } from '@/entities/session';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { Toggle } from '@/shared/ui/Toggle';
import { toast } from '@/shared/ui/toast';
import { invalidateCommunityTargets } from '../model/cache';
import { CommunityReportDialog } from './CommunityReportDialog';
import './community-actions.css';

type ActionTargetType = 'post' | 'review' | 'collection' | 'activity';

type CommunityTargetActionsProps = {
  targetType: ActionTargetType;
  targetId: number;
  reportLabel: string;
  reactionCount?: number | undefined;
  viewerState?:
    | {
        has_liked?: boolean;
        has_bookmarked?: boolean;
      }
    | null
    | undefined;
  className?: string;
  presentation?: 'bar' | 'inline';
  inlineMiddleAction?: ReactNode;
  additionalActions?: ReactNode;
};

export function CommunityTargetActions({
  targetType,
  targetId,
  reportLabel,
  reactionCount,
  viewerState,
  className = '',
  presentation = 'bar',
  inlineMiddleAction,
  additionalActions,
}: CommunityTargetActionsProps) {
  const { t } = useI18n();
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [reportOpen, setReportOpen] = useState(false);
  const showMutationError = () => {
    toast.error(t('common.requestFailed'));
  };
  const reactionMutation = useMutation({
    ...communityMutations.setReaction(),
    onError: showMutationError,
    onSettled: async () => {
      await invalidateCommunityTargets(queryClient);
    },
  });
  const bookmarkMutation = useMutation({
    ...communityMutations.setBookmark(),
    onError: showMutationError,
    onSettled: async () => {
      await invalidateCommunityTargets(queryClient);
    },
  });
  const serverHasLiked = Boolean(viewerState?.has_liked);
  const serverHasBookmarked = Boolean(viewerState?.has_bookmarked);
  const hasLiked = reactionMutation.isPending ? reactionMutation.variables.active : serverHasLiked;
  const hasBookmarked = bookmarkMutation.isPending ? bookmarkMutation.variables.active : serverHasBookmarked;
  const displayedReactionCount =
    typeof reactionCount === 'number'
      ? Math.max(0, reactionCount + Number(hasLiked) - Number(serverHasLiked))
      : undefined;
  const canBookmark = targetType !== 'activity';
  const isInline = presentation === 'inline';
  const rootClassName =
    presentation === 'inline' ? `timeline-action-row ${className}` : `community-action-bar ${className}`;
  const buttonClassName = presentation === 'inline' ? 'timeline-action-button' : 'community-action-button';

  function toggleReaction() {
    if (reactionMutation.isPending) return;
    reactionMutation.mutate({
      active: !hasLiked,
      target_type: targetType,
      target_id: targetId,
      reaction_type: 'like',
    });
  }

  function toggleBookmark() {
    if (bookmarkMutation.isPending) return;
    bookmarkMutation.mutate({
      active: !hasBookmarked,
      target_type: targetType,
      target_id: targetId,
    });
  }

  if (!auth.isAuthenticated) {
    return (
      <div className={rootClassName}>
        <Button asChild className={buttonClassName} size="sm" type="button" variant="unstyled">
          <Link to={routes.login}>{t('community.loginToInteract')}</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className={rootClassName}>
      <Toggle
        className={buttonClassName}
        disabled={reactionMutation.isPending}
        pressed={hasLiked}
        variant="bare"
        onPressedChange={toggleReaction}
      >
        <Heart className="size-4" />
        {isInline ? null : hasLiked ? t('community.liked') : t('community.like')}
        {typeof displayedReactionCount === 'number' ? <span>{displayedReactionCount}</span> : null}
      </Toggle>
      {isInline ? inlineMiddleAction : null}
      {canBookmark ? (
        <Toggle
          className={buttonClassName}
          disabled={bookmarkMutation.isPending}
          pressed={hasBookmarked}
          variant="bare"
          onPressedChange={toggleBookmark}
        >
          <Bookmark className="size-4" />{' '}
          {isInline ? null : hasBookmarked ? t('community.bookmarked') : t('community.bookmark')}
        </Toggle>
      ) : null}
      {additionalActions}
      <Button
        aria-label={t('community.report')}
        className={buttonClassName}
        size="sm"
        type="button"
        variant="unstyled"
        onClick={() => {
          setReportOpen(true);
        }}
      >
        <Flag className="size-4" /> {isInline ? null : t('community.report')}
      </Button>
      <CommunityReportDialog
        label={reportLabel}
        open={reportOpen}
        targetId={targetId}
        targetType={targetType}
        onOpenChange={setReportOpen}
      />
    </div>
  );
}
