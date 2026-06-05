import { type FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, CalendarDays, DatabaseZap, RefreshCw, ShieldCheck } from 'lucide-react';
import { syncMutations, syncQueries, syncQueryKeys } from '@/features/sync/sync-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import type { CalendarSyncResult, IncrementalSyncResult, QueuedTask, SubjectResyncResult, SyncJob, SyncTaskStatus } from '@/lib/api/types';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/Card';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';

const incrementalTaskOptions = [
  '',
  'incremental_subject',
  'incremental_episode',
  'incremental_subject_subject_relation',
  'incremental_subject_staff_relation',
  'incremental_subject_character_relation',
  'incremental_character',
  'incremental_staff',
];
const incrementalTaskValues = incrementalTaskOptions as ReadonlyArray<string>;

type AdminResult = {
  title: string;
  data: unknown;
};

function isQueuedTask(value: unknown): value is QueuedTask {
  return Boolean(value && typeof value === 'object' && 'task_id' in value);
}

function isSubjectResult(value: unknown): value is SubjectResyncResult {
  return Boolean(value && typeof value === 'object' && 'subject_id' in value && 'bangumi_id' in value);
}

function isIncrementalResult(value: unknown): value is { results?: IncrementalSyncResult[] } & Partial<IncrementalSyncResult> {
  return Boolean(value && typeof value === 'object');
}

function isCalendarResult(value: unknown): value is CalendarSyncResult {
  return Boolean(value && typeof value === 'object' && 'weekday_count' in value && 'item_count' in value);
}

function getIncrementalResults(data: unknown) {
  if (!data || typeof data !== 'object') {
    return [];
  }
  if ('results' in data && Array.isArray(data.results)) {
    return data.results as IncrementalSyncResult[];
  }
  if ('task_name' in data && 'processed_count' in data) {
    return [data as IncrementalSyncResult];
  }
  return [];
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

function jobStatusVariant(status: string): 'default' | 'secondary' | 'danger' {
  if (status === 'failed') return 'danger';
  if (status === 'queued' || status === 'running') return 'secondary';
  return 'default';
}

function jobProgress(job: SyncJob) {
  if (job.total_count <= 0) {
    return job.status === 'succeeded' ? 100 : 0;
  }
  return Math.max(0, Math.min(100, Math.round((job.processed_count / job.total_count) * 100)));
}

function ResultPanel({ result }: { result: AdminResult | null }) {
  const { t } = useI18n();

  if (!result) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-200 p-5 text-sm text-neutral-500 dark:border-neutral-800 dark:text-neutral-400">
        {t('admin.noResult')}
      </div>
    );
  }

  const data = result.data;
  return (
    <div className="grid gap-4 rounded-lg border border-neutral-200 p-5 dark:border-neutral-800">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-neutral-400">{t('admin.lastResult')}</p>
          <h3 className="mt-1 font-semibold text-neutral-950 dark:text-white">{result.title}</h3>
        </div>
        {isQueuedTask(data) ? <Badge variant="secondary">{t('admin.queued')}</Badge> : <Badge>{t('admin.completed')}</Badge>}
      </div>

      {isQueuedTask(data) ? (
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-neutral-500 dark:text-neutral-400">Task ID</dt>
            <dd className="mt-1 break-all font-mono text-neutral-950 dark:text-white">{data.task_id}</dd>
          </div>
          <div>
            <dt className="text-neutral-500 dark:text-neutral-400">Status</dt>
            <dd className="mt-1 font-medium text-neutral-950 dark:text-white">{data.status}</dd>
          </div>
          {'bangumi_id' in data ? (
            <div>
              <dt className="text-neutral-500 dark:text-neutral-400">Bangumi ID</dt>
              <dd className="mt-1 font-mono text-neutral-950 dark:text-white">{String(data.bangumi_id)}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {isCalendarResult(data) ? (
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          {[
            ['Weekdays', data.weekday_count],
            ['Items', data.item_count],
            ['Subjects synced', data.synced_subject_count],
            ['Failed subjects', data.failed_subject_count],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-neutral-500 dark:text-neutral-400">{label}</dt>
              <dd className="mt-1 font-medium text-neutral-950 dark:text-white">{String(value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {isSubjectResult(data) ? (
        <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['Bangumi ID', data.bangumi_id],
            ['Subject ID', data.subject_id],
            ['Title', data.title || t('common.untitledSubject')],
            ['Type', data.subject_type],
            ['Staff', data.staff_count],
            ['Characters', data.character_count],
            ['Relations', data.related_subject_count],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-neutral-500 dark:text-neutral-400">{label}</dt>
              <dd className="mt-1 break-all font-medium text-neutral-950 dark:text-white">{String(value)}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {isIncrementalResult(data) && getIncrementalResults(data).length > 0 ? (
        <div className="grid gap-2">
          {getIncrementalResults(data).map((item) => (
            <div className="grid gap-2 rounded-lg bg-neutral-50 p-3 text-sm dark:bg-neutral-900/70 sm:grid-cols-[minmax(0,1.4fr)_repeat(4,minmax(0,0.7fr))]" key={`${item.task_name}-${item.shard}`}>
              <strong className="truncate text-neutral-950 dark:text-white">{item.task_name}</strong>
              <span>{item.processed_count} processed</span>
              <span>{item.synced_count} synced</span>
              <span>{item.skipped_count} skipped</span>
              <span>{item.failed_count} failed</span>
              {item.frontier_reached ? <span className="text-xs font-semibold text-[var(--color-accent-strong)] sm:col-span-5">Frontier reached</span> : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function StatusList({ tasks }: { tasks: SyncTaskStatus[] }) {
  return (
    <div className="grid gap-2">
      {tasks.map((task) => (
        <div className="grid gap-2 rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800 md:grid-cols-[minmax(0,1fr)_120px_120px_120px]" key={`${task.task_name}-${task.shard}`}>
          <div className="min-w-0">
            <p className="truncate font-semibold text-neutral-950 dark:text-white">{task.task_name}</p>
            <p className="truncate text-xs text-neutral-500 dark:text-neutral-400">{task.shard}</p>
          </div>
          <span className="text-neutral-500 dark:text-neutral-400">{task.status}</span>
          <span className="text-neutral-500 dark:text-neutral-400">{task.fail_count} failed</span>
          <span className="text-neutral-500 dark:text-neutral-400">{new Date(task.updated_at).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function SyncJobList({
  isRefreshing,
  jobs,
  onRefresh,
}: {
  isRefreshing: boolean;
  jobs: SyncJob[];
  onRefresh: () => void;
}) {
  const { t } = useI18n();

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>{t('admin.syncRuns')}</CardTitle>
            <CardDescription>{t('admin.syncRunsDescription')}</CardDescription>
          </div>
          <Button disabled={isRefreshing} size="sm" type="button" variant="secondary" onClick={onRefresh}>
            <RefreshCw className={`size-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {t('admin.refresh')}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {jobs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-neutral-200 p-5 text-sm text-neutral-500 dark:border-neutral-800 dark:text-neutral-400">
            {t('admin.noSyncRuns')}
          </div>
        ) : (
          <div className="grid gap-2">
            {jobs.map((job) => {
              const percent = jobProgress(job);
              return (
                <div className="grid gap-3 rounded-lg border border-neutral-200 p-3 dark:border-neutral-800" key={job.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex min-w-0 flex-wrap items-center gap-2">
                        <p className="truncate text-sm font-semibold text-neutral-950 dark:text-white">{jobTypeLabel(job.job_type, t)}</p>
                        <Badge variant={jobStatusVariant(job.status)}>{job.status}</Badge>
                      </div>
                      <p className="mt-1 truncate text-xs text-neutral-500 dark:text-neutral-400">
                        {job.current_label || job.celery_task_id || job.id}
                      </p>
                    </div>
                    <p className="shrink-0 text-xs text-neutral-500 dark:text-neutral-400">
                      {new Date(job.updated_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="grid gap-1.5">
                    <div className="h-1.5 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-900">
                      <div
                        className="h-full rounded-full bg-[var(--color-accent)] transition-[width]"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-neutral-500 dark:text-neutral-400">
                      <span>
                        {job.processed_count}
                        {job.total_count > 0 ? ` / ${job.total_count}` : ''} {t('admin.processed')}
                      </span>
                      <span>{percent}%</span>
                    </div>
                  </div>

                  <div className="grid gap-2 text-xs text-neutral-500 dark:text-neutral-400 sm:grid-cols-4">
                    <span>{job.synced_count} {t('admin.synced')}</span>
                    <span>{job.skipped_count} {t('admin.skipped')}</span>
                    <span>{job.failed_count} {t('admin.failed')}</span>
                    <span>{job.started_at ? `${t('admin.started')} ${new Date(job.started_at).toLocaleTimeString()}` : t('admin.waiting')}</span>
                  </div>
                  {job.error ? <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-950/25 dark:text-red-300">{job.error}</p> : null}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AdminPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [bangumiId, setBangumiId] = useState('');
  const [batchSize, setBatchSize] = useState('100');
  const [taskName, setTaskName] = useState('');
  const [runAsync, setRunAsync] = useState(true);
  const [syncSubjectDetails, setSyncSubjectDetails] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState<AdminResult | null>(null);

  const statusQuery = useQuery(syncQueries.incrementalStatus());
  const syncBangumiMutation = useMutation(syncMutations.syncBangumiSubject());
  const calendarMutation = useMutation(syncMutations.runCalendar());
  const incrementalMutation = useMutation(syncMutations.runIncremental());
  const jobsQuery = useQuery(syncQueries.jobs());

  async function refreshStatus() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: syncQueryKeys.incrementalStatus() }),
      queryClient.invalidateQueries({ queryKey: syncQueryKeys.jobs() }),
    ]);
  }

  async function handleBangumiSync(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage('');
    const parsedBangumiId = Number(bangumiId);
    if (!Number.isInteger(parsedBangumiId) || parsedBangumiId <= 0) {
      setErrorMessage(t('admin.invalidBangumiId'));
      return;
    }

    const data = await syncBangumiMutation.mutateAsync({ bangumi_id: parsedBangumiId, run_async: runAsync });
    setResult({ title: t('admin.bangumiSubject'), data });
    await refreshStatus();
  }

  async function handleCalendarSync() {
    setErrorMessage('');
    const data = await calendarMutation.mutateAsync({ run_async: runAsync, sync_subject_details: syncSubjectDetails });
    setResult({ title: t('admin.calendarSync'), data });
    await refreshStatus();
  }

  async function handleIncrementalSync() {
    setErrorMessage('');
    const parsedBatchSize = Number(batchSize);
    const data = await incrementalMutation.mutateAsync({
      run_async: runAsync,
      batch_size: Number.isInteger(parsedBatchSize) && parsedBatchSize > 0 ? parsedBatchSize : undefined,
      task_name: taskName || undefined,
    });
    setResult({ title: t('admin.incrementalSync'), data });
    await refreshStatus();
  }

  const isPending = syncBangumiMutation.isPending || calendarMutation.isPending || incrementalMutation.isPending;

  return (
    <Page title={t('admin.title')} eyebrow={t('nav.groupMore')}>
      <div className="grid gap-6">
        <section className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <Card>
            <CardHeader>
              <div className="flex items-start gap-3">
                <span className="grid size-10 place-items-center rounded-xl bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]">
                  <DatabaseZap className="size-5" />
                </span>
                <div>
                  <CardTitle>{t('admin.syncTitle')}</CardTitle>
                  <CardDescription>{t('admin.syncDescription')}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-5">
              <form className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]" onSubmit={handleBangumiSync}>
                <label className="grid gap-2">
                  <span className="text-sm font-medium text-neutral-700 dark:text-neutral-200">{t('admin.bangumiSubject')}</span>
                  <Input inputMode="numeric" placeholder={t('admin.bangumiPlaceholder')} value={bangumiId} onChange={(event) => setBangumiId(event.target.value)} />
                </label>
                <Button className="self-end" disabled={isPending} type="submit" variant="accent">
                  {runAsync ? t('admin.queueSync') : t('admin.syncNow')}
                </Button>
              </form>

              {errorMessage ? <p className="text-sm font-medium text-red-600 dark:text-red-400">{errorMessage}</p> : null}

              <div className="grid gap-3 border-t border-neutral-200 pt-5 dark:border-neutral-800 sm:grid-cols-2">
                <label className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300">
                  <input checked={runAsync} className="size-4 accent-[var(--color-accent)]" type="checkbox" onChange={(event) => setRunAsync(event.target.checked)} />
                  {t('admin.runAsync')}
                </label>
                <label className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300">
                  <input checked={syncSubjectDetails} className="size-4 accent-[var(--color-accent)]" type="checkbox" onChange={(event) => setSyncSubjectDetails(event.target.checked)} />
                  {t('admin.syncDetails')}
                </label>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Button disabled={isPending} type="button" variant="secondary" onClick={handleCalendarSync}>
                  <CalendarDays className="size-4" />
                  {t('admin.calendarSync')}
                </Button>
                <Button disabled={isPending} type="button" variant="secondary" onClick={handleIncrementalSync}>
                  <Activity className="size-4" />
                  {t('admin.incrementalSync')}
                </Button>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="grid gap-2">
                  <span className="text-sm font-medium text-neutral-700 dark:text-neutral-200">{t('admin.taskName')}</span>
                  <FilterMenu
                    label=""
                    options={incrementalTaskValues.map((option) => ({ label: option || t('admin.allTasks'), value: option }))}
                    value={taskName}
                    onChange={setTaskName}
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-medium text-neutral-700 dark:text-neutral-200">{t('admin.batchSize')}</span>
                  <Input inputMode="numeric" value={batchSize} onChange={(event) => setBatchSize(event.target.value)} />
                </label>
              </div>
            </CardContent>
          </Card>

          <aside className="grid gap-4">
            <Card>
              <CardHeader>
                <CardTitle>{t('admin.lastResult')}</CardTitle>
              </CardHeader>
              <CardContent>
                <ResultPanel result={result} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-start gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-[var(--color-accent-soft)] text-[var(--color-accent-strong)]">
                    <ShieldCheck className="size-4" />
                  </span>
                  <div className="min-w-0">
                    <CardTitle>{t('admin.reportsTitle')}</CardTitle>
                    <CardDescription>{t('admin.reportsDescription')}</CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Card>
          </aside>
        </section>

        <SyncJobList
          isRefreshing={jobsQuery.isFetching}
          jobs={jobsQuery.data?.jobs ?? []}
          onRefresh={() => {
            void refreshStatus();
          }}
        />

        <section>
          <Card>
            <CardHeader>
              <CardTitle>{t('admin.statusTitle')}</CardTitle>
              <CardDescription>{t('admin.statusDescription')}</CardDescription>
            </CardHeader>
            <CardContent>
              {statusQuery.isLoading ? <LoadingState title={t('common.loading')} /> : null}
              {statusQuery.isError ? <ErrorState title={t('search.errorTitle')} description={t('search.errorBody')} /> : null}
              {statusQuery.data ? <StatusList tasks={statusQuery.data.tasks} /> : null}
            </CardContent>
          </Card>
        </section>
      </div>
    </Page>
  );
}
