import { RefreshCw } from 'lucide-react';
import type {
  CalendarSyncResult,
  IncrementalSyncResult,
  IncrementalSyncRunResult,
  QueuedTask,
  SubjectResyncResult,
  SyncJob,
  SyncTaskStatus,
} from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { formatDateTime, formatTime } from '@/shared/lib/date';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { ListSurface } from '@/shared/ui/DataView';
import { Pagination } from '@/shared/ui/Pagination';

export type AdminSyncResult =
  | {
      kind: 'bangumi';
      title: string;
      data: (QueuedTask & { bangumi_id: number }) | SubjectResyncResult;
    }
  | {
      kind: 'calendar';
      title: string;
      data: QueuedTask | CalendarSyncResult;
    }
  | {
      kind: 'incremental';
      title: string;
      data: IncrementalSyncRunResult;
    };

function getIncrementalResults(data: Exclude<IncrementalSyncRunResult, QueuedTask>): IncrementalSyncResult[] {
  return 'results' in data ? data.results : [data];
}

function jobTypeLabel(jobType: string, t: ReturnType<typeof useI18n>['t']) {
  const labels: Record<string, string> = {
    subject_bangumi: t('admin.jobSubjectBangumi'),
    subject_resync: t('admin.jobSubjectResync'),
    calendar: t('admin.jobCalendar'),
    incremental: t('admin.jobIncremental'),
  };
  return labels[jobType] ?? jobType.replaceAll('_', ' ');
}

function jobStatusVariant(status: string): 'accent' | 'danger' | 'secondary' | 'success' {
  if (status === 'failed') return 'danger';
  if (status === 'succeeded') return 'success';
  if (status === 'running') return 'accent';
  return 'secondary';
}

function jobProgress(job: SyncJob) {
  if (job.total_count <= 0) return job.status === 'succeeded' ? 100 : 0;
  return Math.max(0, Math.min(100, Math.round((job.processed_count / job.total_count) * 100)));
}

export function AdminResultPanel({ result }: { result: AdminSyncResult | null }) {
  const { t } = useI18n();

  if (!result) {
    return (
      <div
        className="grid min-h-40 place-items-center rounded-sm border border-dashed border-border bg-surface px-4 py-6 text-center"
        data-slot="admin-result-empty"
      >
        <p className="m-0 max-w-56 text-xs leading-5 text-muted-foreground">{t('admin.noResult')}</p>
      </div>
    );
  }

  const data = result.data;
  const incrementalResults =
    result.kind === 'incremental' && !('task_id' in result.data) ? getIncrementalResults(result.data) : [];
  return (
    <div className="grid min-w-0 gap-4" data-slot="admin-result-panel">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <h3 className="m-0 min-w-0 truncate text-[13px] font-semibold leading-5 text-foreground">{result.title}</h3>
        {'task_id' in data ? (
          <Badge variant="secondary">{t('admin.queued')}</Badge>
        ) : (
          <Badge variant="success">{t('admin.completed')}</Badge>
        )}
      </div>

      {'task_id' in data ? (
        <dl className="divide-y divide-border-subtle rounded-sm bg-muted px-3 text-xs" data-slot="admin-result-details">
          <div className="grid grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)] gap-3 py-2">
            <dt className="text-muted-foreground">Task ID</dt>
            <dd className="m-0 break-all text-right font-mono text-foreground">{data.task_id}</dd>
          </div>
          <div className="grid grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)] gap-3 py-2">
            <dt className="text-muted-foreground">Status</dt>
            <dd className="m-0 break-all text-right font-medium text-foreground">{data.status}</dd>
          </div>
          {'bangumi_id' in data ? (
            <div className="grid grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)] gap-3 py-2">
              <dt className="text-muted-foreground">Bangumi ID</dt>
              <dd className="m-0 text-right font-mono text-foreground">{String(data.bangumi_id)}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {result.kind === 'calendar' && !('task_id' in result.data) ? (
        <dl className="divide-y divide-border-subtle rounded-sm bg-muted px-3 text-xs" data-slot="admin-result-details">
          {[
            ['Weekdays', result.data.weekday_count],
            ['Items', result.data.item_count],
            ['Subjects synced', result.data.synced_subject_count],
            ['Failed subjects', result.data.failed_subject_count],
          ].map(([label, value]) => (
            <div className="flex items-center justify-between gap-3 py-2" key={label}>
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="m-0 font-medium tabular-nums text-foreground">{String(value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {result.kind === 'bangumi' && !('task_id' in result.data) ? (
        <dl className="divide-y divide-border-subtle rounded-sm bg-muted px-3 text-xs" data-slot="admin-result-details">
          {[
            ['Bangumi ID', result.data.bangumi_id],
            ['Subject ID', result.data.subject_id],
            ['Title', result.data.title || t('common.untitledSubject')],
            ['Type', result.data.subject_type],
            ['Staff', result.data.staff_count],
            ['Characters', result.data.character_count],
            ['Relations', result.data.related_subject_count],
          ].map(([label, value]) => (
            <div className="grid grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)] gap-3 py-2" key={label}>
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="m-0 break-all text-right font-medium text-foreground">{String(value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {incrementalResults.length > 0 ? (
        <div className="divide-y divide-border-subtle rounded-sm bg-muted px-3" data-slot="admin-incremental-results">
          {incrementalResults.map((item) => (
            <div className="grid min-w-0 gap-2 py-3 text-xs" key={`${item.task_name}-${item.shard}`}>
              <div className="flex min-w-0 items-center justify-between gap-2">
                <strong className="truncate font-medium text-foreground">{item.task_name}</strong>
                <span className="shrink-0 text-subtle-foreground">{item.shard}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-muted-foreground">
                <span className="tabular-nums">
                  {item.processed_count} {t('admin.processed')}
                </span>
                <span className="tabular-nums">
                  {item.synced_count} {t('admin.synced')}
                </span>
                <span className="tabular-nums">
                  {item.skipped_count} {t('admin.skipped')}
                </span>
                <span className={cn('tabular-nums', item.failed_count > 0 && 'text-[var(--ui-danger-text)]')}>
                  {item.failed_count} {t('admin.failed')}
                </span>
              </div>
              {item.frontier_reached ? <Badge variant="accent">Frontier reached</Badge> : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function AdminStatusList({ tasks }: { tasks: SyncTaskStatus[] }) {
  const { t } = useI18n();

  return (
    <ListSurface role="list" data-slot="admin-status-list">
      {tasks.map((task) => (
        <div
          className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 border-b border-border-subtle px-3 py-3 text-xs last:border-b-0 md:grid-cols-[minmax(0,1fr)_7rem_7rem_10rem] md:px-4"
          data-slot="admin-status-row"
          key={`${task.task_name}-${task.shard}`}
          role="listitem"
        >
          <div className="min-w-0">
            <p className="m-0 truncate font-medium text-foreground">{task.task_name}</p>
            <p className="m-0 mt-0.5 truncate text-subtle-foreground">{task.shard}</p>
          </div>
          <Badge variant={jobStatusVariant(task.status)}>{task.status}</Badge>
          <span
            className={cn(
              'col-start-1 row-start-2 tabular-nums text-muted-foreground md:col-auto md:row-auto',
              task.fail_count > 0 && 'text-[var(--ui-danger-text)]',
            )}
          >
            {task.fail_count} {t('admin.failed')}
          </span>
          <time
            className="col-start-2 row-start-2 text-right text-subtle-foreground md:col-auto md:row-auto md:text-left"
            dateTime={task.updated_at}
          >
            {formatDateTime(task.updated_at)}
          </time>
        </div>
      ))}
    </ListSurface>
  );
}

export function AdminSyncJobList({
  currentPage,
  isRefreshing,
  jobs,
  onRefresh,
  onPageChange,
  totalPages,
}: {
  currentPage: number;
  isRefreshing: boolean;
  jobs: SyncJob[];
  onRefresh: () => void;
  onPageChange: (page: number) => void;
  totalPages: number;
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
            const jobLabel = jobTypeLabel(job.job_type, t);
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
                      {job.current_label || job.celery_task_id || job.id}
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
                      {job.processed_count}
                      {job.total_count > 0 ? ` / ${job.total_count}` : ''} {t('admin.processed')}
                    </span>
                    <span className="tabular-nums text-subtle-foreground">{percent}%</span>
                  </div>
                </div>

                <div className="flex min-w-0 flex-wrap gap-x-4 gap-y-1 border-t border-border-subtle pt-2 text-xs text-muted-foreground">
                  <span className="tabular-nums">
                    <strong className="font-medium text-foreground">{job.synced_count}</strong> {t('admin.synced')}
                  </span>
                  <span className="tabular-nums">
                    <strong className="font-medium text-foreground">{job.skipped_count}</strong> {t('admin.skipped')}
                  </span>
                  <span className={cn('tabular-nums', job.failed_count > 0 && 'text-[var(--ui-danger-text)]')}>
                    <strong className="font-medium">{job.failed_count}</strong> {t('admin.failed')}
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
      <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={onPageChange} />
    </section>
  );
}
