import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { Link } from '@tanstack/react-router';
import { activityTitle, activityTypeLabel } from '@/entities/community';
import type { Activity } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { formatDate } from '@/shared/lib/date';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { ListSurface } from '@/shared/ui/DataView';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';

const coverPlaceholder = placeholderImagePaths.subjectCover;

export function ProfileActivityTimeline({
  activities,
  hasNextPage,
  isError,
  isFetchingNextPage,
  isLoading,
  onLoadMore,
}: {
  activities: Activity[];
  hasNextPage: boolean;
  isError: boolean;
  isFetchingNextPage: boolean;
  isLoading: boolean;
  onLoadMore: () => void;
}) {
  const { t } = useI18n();

  return (
    <div className="grid min-w-0 gap-4" data-slot="profile-activity-timeline">
      {isLoading ? <LoadingState title={t('me.dashboard.loadingActivity')} /> : null}
      {isError ? (
        <ErrorState title={t('profile.contentErrorTitle')} description={t('profile.contentErrorBody')} />
      ) : null}
      {!isLoading && !isError && activities.length > 0 ? (
        <ListSurface>
          {activities.map((activity) => (
            <article
              className="grid min-w-0 grid-cols-[10px_minmax(0,1fr)] gap-3 border-b border-border-subtle px-3 py-3 last:border-b-0 sm:px-4"
              data-slot="profile-activity-row"
              key={activity.id}
            >
              <span aria-hidden="true" className="mt-1.5 size-2 rounded-full bg-[var(--ui-border-strong)]" />
              <div className="min-w-0">
                <p className="line-clamp-2 text-sm font-semibold leading-5 text-foreground">
                  {activityTitle(activity, activity.activity_type.replaceAll('_', ' '))}
                </p>
                <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                  <span>{activityTypeLabel(activity.activity_type, t)}</span>
                  <span aria-hidden="true" className="text-[var(--ui-border-strong)]">
                    ·
                  </span>
                  <time className="text-subtle-foreground" dateTime={activity.created_at}>
                    {formatDate(activity.created_at)}
                  </time>
                </div>
                {activity.subject ? (
                  <Link
                    className="mt-3 grid min-w-0 grid-cols-[36px_minmax(0,1fr)] items-center gap-2.5 border-l-2 border-border px-2 py-1.5 transition-colors hover:border-[var(--ui-accent-border)] hover:bg-muted"
                    data-slot="profile-activity-subject"
                    to={routes.subject(activity.subject.id)}
                  >
                    <img
                      alt=""
                      className="h-12 w-9 rounded-sm bg-muted object-cover"
                      decoding="async"
                      loading="lazy"
                      referrerPolicy="no-referrer"
                      src={activity.subject.image_thumbnail || activity.subject.image || coverPlaceholder}
                    />
                    <span className="grid min-w-0 content-center gap-1">
                      <span className="line-clamp-1 text-sm font-semibold text-foreground">
                        {activity.subject.display_title || activity.subject.title}
                      </span>
                      <span className="line-clamp-1 text-xs text-muted-foreground">
                        {activity.subject.display_subtitle || activity.subject.subject_type}
                      </span>
                    </span>
                  </Link>
                ) : null}
              </div>
            </article>
          ))}
        </ListSurface>
      ) : null}
      {!isLoading && !isError && activities.length === 0 ? (
        <EmptyState title={t('me.dashboard.noActivityTitle')} description={t('me.dashboard.noActivityBody')} />
      ) : null}
      {!isLoading && !isError && activities.length > 0 ? (
        <div className="flex justify-center pt-1 text-sm text-muted-foreground" data-slot="activity-pagination">
          {hasNextPage ? (
            <Button disabled={isFetchingNextPage} type="button" variant="secondary" onClick={onLoadMore}>
              {isFetchingNextPage ? t('me.dashboard.loadingMore') : t('me.dashboard.loadMore')}
            </Button>
          ) : (
            <span>{t('me.dashboard.activityEnd')}</span>
          )}
        </div>
      ) : null}
    </div>
  );
}
