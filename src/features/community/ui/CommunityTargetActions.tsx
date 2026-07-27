import { type FormEvent, type ReactNode, useEffect, useState } from 'react';
import { Link } from '@/shared/routing/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Bookmark, Flag, Heart } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { invalidateCommunityTargets } from '../model/cache';
import { communityMutations } from '@/entities/community';
import { useI18n } from '@/shared/i18n';
import type { CommunityReportReason } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';

const reportReasons = ['spam', 'harassment', 'spoiler', 'illegal', 'other'] as const satisfies CommunityReportReason[];

type ActionTargetType = 'review' | 'collection' | 'activity';

type CommunityTargetActionsProps = {
  targetType: ActionTargetType;
  targetId: number;
  reportLabel: string;
  reactionCount?: number;
  viewerState?: {
    has_liked?: boolean;
    has_bookmarked?: boolean;
  } | null;
  className?: string;
  presentation?: 'bar' | 'inline';
  inlineMiddleAction?: ReactNode;
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
}: CommunityTargetActionsProps) {
  const { t } = useI18n();
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [hasLiked, setHasLiked] = useState(Boolean(viewerState?.has_liked));
  const [hasBookmarked, setHasBookmarked] = useState(Boolean(viewerState?.has_bookmarked));
  const [localReactionCount, setLocalReactionCount] = useState(reactionCount);
  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState<CommunityReportReason>('spam');
  const [reportDescription, setReportDescription] = useState('');

  useEffect(() => {
    setHasLiked(Boolean(viewerState?.has_liked));
    setHasBookmarked(Boolean(viewerState?.has_bookmarked));
    setLocalReactionCount(reactionCount);
  }, [reactionCount, viewerState?.has_bookmarked, viewerState?.has_liked]);

  const invalidateCommunity = async () => {
    await invalidateCommunityTargets(queryClient);
  };

  const reactMutation = useMutation({
    ...communityMutations.react(),
    onSuccess: async () => {
      setHasLiked(true);
      setLocalReactionCount((current) => (typeof current === 'number' ? current + 1 : current));
      await invalidateCommunity();
    },
  });
  const unreactMutation = useMutation({
    ...communityMutations.unreact(),
    onSuccess: async () => {
      setHasLiked(false);
      setLocalReactionCount((current) => (typeof current === 'number' ? Math.max(0, current - 1) : current));
      await invalidateCommunity();
    },
  });
  const bookmarkMutation = useMutation({
    ...communityMutations.bookmark(),
    onSuccess: async () => {
      setHasBookmarked(true);
      await invalidateCommunity();
    },
  });
  const unbookmarkMutation = useMutation({
    ...communityMutations.unbookmark(),
    onSuccess: async () => {
      setHasBookmarked(false);
      await invalidateCommunity();
    },
  });
  const reportMutation = useMutation({
    ...communityMutations.createReport(),
    onSuccess: async () => {
      setReportOpen(false);
      setReportReason('spam');
      setReportDescription('');
      await invalidateCommunity();
    },
  });

  const isPending =
    reactMutation.isPending ||
    unreactMutation.isPending ||
    bookmarkMutation.isPending ||
    unbookmarkMutation.isPending ||
    reportMutation.isPending;
  const canBookmark = targetType !== 'activity';
  const isInline = presentation === 'inline';
  const rootClassName =
    presentation === 'inline' ? `timeline-action-row ${className}` : `community-action-bar ${className}`;
  const buttonClassName = presentation === 'inline' ? 'timeline-action-button' : 'community-action-button';
  const activeButtonClassName =
    presentation === 'inline' ? `${buttonClassName} is-active` : `${buttonClassName} is-active`;

  function toggleReaction() {
    const body = { target_type: targetType, target_id: targetId, reaction_type: 'like' as const };
    if (hasLiked) unreactMutation.mutate(body);
    else reactMutation.mutate(body);
  }

  function toggleBookmark() {
    const body = { target_type: targetType, target_id: targetId };
    if (hasBookmarked) unbookmarkMutation.mutate(body);
    else bookmarkMutation.mutate(body);
  }

  function submitReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    reportMutation.mutate({
      target_type: targetType,
      target_id: targetId,
      reason: reportReason,
      description: reportDescription,
    });
  }

  if (!auth.isAuthenticated) {
    return (
      <div className={rootClassName}>
        <Button asChild className={buttonClassName} size="sm" type="button" variant="ghost">
          <Link to={routes.login}>{t('community.loginToInteract')}</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className={rootClassName}>
      <Button
        className={hasLiked ? activeButtonClassName : buttonClassName}
        disabled={isPending}
        size="sm"
        type="button"
        variant="ghost"
        onClick={toggleReaction}
      >
        <Heart className="size-4" />
        {isInline ? null : hasLiked ? t('community.liked') : t('community.like')}
        {typeof localReactionCount === 'number' ? <span>{localReactionCount}</span> : null}
      </Button>
      {isInline ? inlineMiddleAction : null}
      {canBookmark ? (
        <Button
          className={hasBookmarked ? activeButtonClassName : buttonClassName}
          disabled={isPending}
          size="sm"
          type="button"
          variant="ghost"
          onClick={toggleBookmark}
        >
          <Bookmark className="size-4" />{' '}
          {isInline ? null : hasBookmarked ? t('community.bookmarked') : t('community.bookmark')}
        </Button>
      ) : null}
      <Button
        aria-label={t('community.report')}
        className={buttonClassName}
        size="sm"
        type="button"
        variant="ghost"
        onClick={() => setReportOpen(true)}
      >
        <Flag className="size-4" /> {isInline ? null : t('community.report')}
      </Button>

      <Dialog open={reportOpen} onOpenChange={setReportOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('community.reportTitle')}</DialogTitle>
            <DialogDescription>{reportLabel || t('community.reportDescription')}</DialogDescription>
          </DialogHeader>
          <form className="grid gap-4" onSubmit={submitReport}>
            <div className="grid gap-2">
              <span className="text-sm font-semibold text-[var(--color-text)]">{t('community.reportReason')}</span>
              <div className="flex flex-wrap gap-2">
                {reportReasons.map((reason) => (
                  <button
                    className={[
                      'rounded-full border px-3 py-1.5 text-sm font-semibold transition',
                      reportReason === reason
                        ? 'border-[var(--color-accent-border)] bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]'
                        : 'border-[var(--color-border)] text-[var(--color-text-muted)] hover:border-[var(--color-accent-border)]',
                    ].join(' ')}
                    key={reason}
                    type="button"
                    onClick={() => setReportReason(reason)}
                  >
                    {t(`community.reportReason.${reason}`)}
                  </button>
                ))}
              </div>
            </div>
            <textarea
              className="min-h-28 resize-y rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-sm leading-6 text-[var(--color-text)] outline-none transition placeholder:text-neutral-400 focus:border-[var(--color-accent-border)]"
              value={reportDescription}
              placeholder={t('community.reportPlaceholder')}
              onChange={(event) => setReportDescription(event.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setReportOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button disabled={reportMutation.isPending} type="submit">
                <Flag className="size-4" /> {t('community.submitReport')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
