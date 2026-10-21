import { RefreshCw } from 'lucide-react';
import type { ImportJob } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { formatDateTime, formatTime } from '@/shared/lib/date';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ListSurface } from '@/shared/ui/DataView';

function jobTypeLabel(job: ImportJob) {
  return job.provider || job.id;
}

function jobStatusVariant(status: string): 'accent' | 'danger' | 'secondary' | 'success' {
  if (status === 'failed') return 'danger';
  if (status === 'succeeded') return 'success';
  if (status === 'running') return 'accent';
  return 'secondary';
}

function jobProgress(job: ImportJob) {
  if (job.progress.total <= 0) return job.status === 'succeeded' ? 100 : 0;
  return Math.max(0, Math.min(100, Math.round((job.progress.processed / job.progress.total) * 100)));
}

export function AdminSyncJobList({
  isRefreshing,
  jobs,
  hasNextPage,
  onLoadMore,
  onRefresh,
}: {
  cursor?: string;
  hasNextPage: boolean;
  isRefreshing: boolean;
  jobs: ImportJob[];
  onLoadMore: () => void;
  onRefresh: () => void;
}) {
  const { t } = useI18n();

  return (
    <section
      aria-labelledby="admin-sync-runs-title"
      className="grid min-w-0 gap-3 border-t border-border-subtle pt-5"
      data-slot="admin-sync-job-list"
    >
      <header className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="m-0 text-sm font-semibold leading-5 text-foreground" id="admin-sync-runs-title">
            {t('admin.syncRuns')}
          </h2>
          <p className="m-0 mt-0.5 text-xs leading-5 text-muted-foreground">{t('admin.syncRunsDescription')}</p>
        </div>
        <Button disabled={isRefreshing} size="sm" type="button" variant="secondary" onClick={onRefresh}>
          <RefreshCw className={cn('size-4', isRefreshing && 'animate-spin')} />
          {t('admin.refresh')}
        </Button>
      </header>
      {jobs.length === 0 ? (
        <div className="rounded-sm border border-dashed border-border px-4 py-5 text-xs text-muted-foreground">
          {t('admin.noSyncRuns')}
        </div>
      ) : (
        <ListSurface data-slot="admin-sync-runs">
          {jobs.map((job) => {
            const percent = jobProgress(job);
            const jobLabel = jobTypeLabel(job);
            return (
              <article
                className="grid min-w-0 gap-3 border-b border-border-subtle px-3 py-3 last:border-b-0 sm:px-4"
                data-slot="admin-sync-run"
                key={job.id}
              >
                <header className="flex min-w-0 flex-wrap items-start justify-between gap-x-4 gap-y-1.5">
                  <div className="min-w-0">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <h3 className="m-0 truncate text-[13px] font-semibold leading-5 text-foreground">{jobLabel}</h3>
                      <Badge variant={jobStatusVariant(job.status)}>{job.status}</Badge>
                    </div>
                    <p className="m-0 mt-0.5 truncate text-xs text-muted-foreground">
                      {job.progress.current_label || job.id}
                    </p>
                  </div>
                  <time className="shrink-0 text-xs text-subtle-foreground" dateTime={job.updated_at}>
                    {formatDateTime(job.updated_at)}
                  </time>
                </header>

                <div className="grid gap-1.5" data-slot="admin-sync-progress">
                  <div
                    aria-label={`${jobLabel}: ${percent}%`}
                    aria-valuemax={100}
                    aria-valuemin={0}
                    aria-valuenow={percent}
                    className="h-1 overflow-hidden rounded-[2px] bg-muted"
                    role="progressbar"
                  >
                    <div
                      className="h-full bg-brand transition-[width] duration-[var(--ui-transition-fast)]"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
                    <span className="tabular-nums">
                      {job.progress.processed}
                      {job.progress.total > 0 ? ` / ${job.progress.total}` : ''} {t('admin.processed')}
                    </span>
                    <span className="tabular-nums text-subtle-foreground">{percent}%</span>
                  </div>
                </div>

                <div className="flex min-w-0 flex-wrap gap-x-4 gap-y-1 border-t border-border-subtle pt-2 text-xs text-muted-foreground">
                  <span className="tabular-nums">
                    <strong className="font-medium text-foreground">{job.progress.synced}</strong> {t('admin.synced')}
                  </span>
                  <span className="tabular-nums">
                    <strong className="font-medium text-foreground">{job.progress.skipped}</strong> {t('admin.skipped')}
                  </span>
                  <span className={cn('tabular-nums', job.progress.failed > 0 && 'text-[var(--ui-danger-text)]')}>
                    <strong className="font-medium">{job.progress.failed}</strong> {t('admin.failed')}
                  </span>
                  <span className="sm:ml-auto">
                    {job.started_at ? `${t('admin.started')} ${formatTime(job.started_at)}` : t('admin.waiting')}
                  </span>
                </div>

                {job.error ? (
                  <p className="m-0 border-l-2 border-[var(--ui-danger)] bg-[var(--ui-danger-soft)] px-3 py-2 text-xs leading-5 text-[var(--ui-danger-text)]">
                    {job.error}
                  </p>
                ) : null}
              </article>
            );
          })}
        </ListSurface>
      )}
      {hasNextPage ? (
        <Button disabled={isRefreshing} size="sm" type="button" variant="secondary" onClick={onLoadMore}>
          {t('community.loadMore')}
        </Button>
      ) : null}
    </section>
  );
}
