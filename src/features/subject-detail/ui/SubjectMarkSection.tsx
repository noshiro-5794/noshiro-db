import { useId } from 'react';
import { Link } from '@tanstack/react-router';
import { PencilLine, Plus, Star } from 'lucide-react';
import type { UserSubjectContext } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { DetailSection } from '@/shared/ui/Detail';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { StarRatingDisplay } from './RatingStars';

export function SubjectMarkSection({
  className,
  context,
  finishedCount,
  isAuthenticated,
  isError,
  isLoading,
  loginState,
  totalCount,
  onEdit,
  onRetry,
}: {
  className?: string;
  context: UserSubjectContext | undefined;
  finishedCount: number;
  isAuthenticated: boolean;
  isError: boolean;
  isLoading: boolean;
  loginState: RouteBackState;
  totalCount: number;
  onEdit: () => void;
  onRetry: () => void;
}) {
  const { t } = useI18n();
  const titleId = useId();
  const emptyText = t('common.none');
  const userSubject = context?.user_subject ?? null;
  const statusLabels: Record<string, string> = {
    wish: t('status.wish'),
    doing: t('status.doing'),
    done: t('status.done'),
    on_hold: t('status.onHold'),
    drop: t('status.drop'),
  };
  const statusLabel = statusLabels[userSubject?.status ?? ''] ?? userSubject?.status ?? '';
  const markMeta = userSubject
    ? `${statusLabel} · ${t(userSubject.is_public ? 'common.public' : 'common.private')}`
    : undefined;
  const action = isAuthenticated ? (
    <Button disabled={!context || isLoading || isError} size="sm" type="button" variant="secondary" onClick={onEdit}>
      {userSubject ? <PencilLine aria-hidden="true" /> : <Plus aria-hidden="true" />}
      {userSubject ? t('subject.editMark') : t('subject.markSubject')}
    </Button>
  ) : (
    <Button asChild size="sm" variant="secondary">
      <Link state={loginState} to={routes.login}>
        {t('auth.login')}
      </Link>
    </Button>
  );

  return (
    <DetailSection
      actions={action}
      className={className}
      id="mark"
      meta={markMeta}
      title={t('subject.mark')}
      titleId={titleId}
    >
      {isAuthenticated && isLoading ? <LoadingState title={t('subject.mark')} /> : null}
      {isAuthenticated && isError ? (
        <ErrorState
          action={
            <Button size="sm" variant="secondary" onClick={onRetry}>
              {t('common.retry')}
            </Button>
          }
          description={t('common.requestFailed')}
          title={t('subject.mark')}
        />
      ) : null}
      {!isLoading && !isError && userSubject ? (
        <div className="grid gap-3">
          <dl className="grid grid-cols-3 divide-x divide-border-subtle rounded-sm bg-muted">
            <div className="min-w-0 px-2 py-2.5 sm:px-3">
              <dt className="text-[11px] font-medium text-subtle-foreground">{t('subject.progress')}</dt>
              <dd className="mt-1 truncate text-sm font-semibold tabular-nums text-foreground">
                {finishedCount} / {totalCount}
              </dd>
            </div>
            <div className="min-w-0 px-2 py-2.5 sm:px-3">
              <dt className="text-[11px] font-medium text-subtle-foreground">{t('subject.simple')}</dt>
              <dd className="mt-1 overflow-hidden">
                <StarRatingDisplay emptyLabel={emptyText} value={userSubject.simple_rating} />
              </dd>
            </div>
            <div className="min-w-0 px-2 py-2.5 sm:px-3">
              <dt className="text-[11px] font-medium text-subtle-foreground">{t('subject.rating')}</dt>
              <dd className="mt-1 truncate text-sm font-semibold tabular-nums text-foreground">
                {userSubject.rating ?? emptyText}
              </dd>
            </div>
          </dl>
          {context?.tags.length ? (
            <div className="flex flex-wrap gap-1.5">
              {context.tags.map((tag) => (
                <Badge key={tag.id}>{tag.name}</Badge>
              ))}
            </div>
          ) : null}
          {context?.rating_details.length ? (
            <dl className="divide-y divide-border-subtle rounded-sm bg-muted px-3 text-sm">
              {context.rating_details.map((detail) => (
                <div className="flex items-center justify-between gap-3 py-2" key={detail.key}>
                  <dt className="min-w-0 truncate text-muted-foreground">{detail.key}</dt>
                  <dd className="shrink-0 font-semibold tabular-nums text-foreground">{detail.value}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          {userSubject.comment ? (
            <p className="m-0 border-l-2 border-[var(--ui-accent-border)] pl-3 text-sm leading-6 text-muted-foreground">
              {userSubject.comment}
            </p>
          ) : null}
        </div>
      ) : null}
      {!isLoading && !isError && !userSubject ? (
        <div className="flex min-h-12 items-center gap-2 rounded-sm bg-muted px-3 py-3 text-sm text-muted-foreground">
          <Star aria-hidden="true" className="size-4 shrink-0 text-[var(--ui-accent-text)]" />
          <span>{isAuthenticated ? t('subject.notMarked') : t('subject.loginToMark')}</span>
        </div>
      ) : null}
    </DetailSection>
  );
}
