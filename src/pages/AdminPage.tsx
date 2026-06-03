import { type FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, CalendarDays, DatabaseZap, ShieldCheck } from 'lucide-react';
import { syncMutations, syncQueries, syncQueryKeys } from '@/features/sync/sync-queries';
import type { IncrementalSyncResult, QueuedTask, SubjectResyncResult, SyncTaskStatus } from '@/lib/api/types';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/Card';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';
import { useI18n } from '@/features/i18n/use-i18n';

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
          {'bangumi_id' in data ? (
            <div>
              <dt className="text-neutral-500 dark:text-neutral-400">Bangumi ID</dt>
              <dd className="mt-1 font-mono text-neutral-950 dark:text-white">{String(data.bangumi_id)}</dd>
            </div>
          ) : null}
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

      {isIncrementalResult(data) && Array.isArray(data.results) ? (
        <div className="grid gap-2">
          {data.results.map((item) => (
            <div className="grid gap-2 rounded-lg bg-neutral-50 p-3 text-sm dark:bg-neutral-900/70 sm:grid-cols-4" key={`${item.task_name}-${item.shard}`}>
              <strong className="text-neutral-950 dark:text-white">{item.task_name}</strong>
              <span>{item.synced_count} synced</span>
              <span>{item.skipped_count} skipped</span>
              <span>{item.failed_count} failed</span>
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

  async function refreshStatus() {
    await queryClient.invalidateQueries({ queryKey: syncQueryKeys.incrementalStatus() });
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
    <Page title={t('admin.title')} eyebrow={t('auth.admin')} description={t('admin.description')}>
      <div className="grid gap-6">
        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
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

          <Card>
            <CardHeader>
              <CardTitle>{t('admin.lastResult')}</CardTitle>
              <CardDescription>{t('admin.noResult')}</CardDescription>
            </CardHeader>
            <CardContent>
              <ResultPanel result={result} />
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
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

          <Card>
            <CardHeader>
              <div className="flex items-start gap-3">
                <span className="grid size-10 place-items-center rounded-xl bg-neutral-100 text-neutral-600 dark:bg-neutral-900 dark:text-neutral-300">
                  <ShieldCheck className="size-5" />
                </span>
                <div>
                  <CardTitle>{t('admin.reportsTitle')}</CardTitle>
                  <CardDescription>{t('admin.reportsDescription')}</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        </section>
      </div>
    </Page>
  );
}
