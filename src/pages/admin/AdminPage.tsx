import { type SyntheticEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, CalendarDays, DatabaseZap } from 'lucide-react';
import {
  AdminResultPanel,
  AdminStatusList,
  AdminSyncJobList,
  syncMutations,
  syncQueries,
  syncQueryKeys,
  type AdminSyncResult,
} from '@/features/admin-sync';
import { useI18n } from '@/shared/i18n';
import { getErrorMessage } from '@/shared/lib/error';
import { parseIntegerParam } from '@/shared/routing/search-params';
import { Button } from '@/shared/ui/Button';
import { CheckboxField } from '@/shared/ui/Checkbox';
import { ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';

const incrementalTaskValues = [
  '',
  'incremental_subject',
  'incremental_episode',
  'incremental_subject_subject_relation',
  'incremental_subject_staff_relation',
  'incremental_subject_character_relation',
  'incremental_character',
  'incremental_staff',
] as const;
const jobPageSize = 8;

export function AdminPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [bangumiId, setBangumiId] = useState('');
  const [batchSize, setBatchSize] = useState('100');
  const [taskName, setTaskName] = useState('');
  const [runAsync, setRunAsync] = useState(true);
  const [syncSubjectDetails, setSyncSubjectDetails] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState<AdminSyncResult | null>(null);
  const [jobPage, setJobPage] = useState(1);

  const statusQuery = useQuery(syncQueries.incrementalStatus());
  const syncBangumiMutation = useMutation(syncMutations.syncBangumiSubject());
  const calendarMutation = useMutation(syncMutations.runCalendar());
  const incrementalMutation = useMutation(syncMutations.runIncremental());
  const jobsQuery = useQuery(syncQueries.jobs({ page: jobPage, page_size: jobPageSize }));

  async function refreshStatus() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: syncQueryKeys.incrementalStatus() }),
      queryClient.invalidateQueries({ queryKey: syncQueryKeys.jobs() }),
    ]);
  }

  async function handleBangumiSync(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    setErrorMessage('');
    const parsedBangumiId = parseIntegerParam(bangumiId, { min: 1 });
    if (!parsedBangumiId) {
      setErrorMessage(t('admin.invalidBangumiId'));
      return;
    }

    try {
      const data = await syncBangumiMutation.mutateAsync({ bangumi_id: parsedBangumiId, run_async: runAsync });
      setResult({ kind: 'bangumi', title: t('admin.bangumiSubject'), data });
      setJobPage(1);
      await refreshStatus();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    }
  }

  async function handleCalendarSync() {
    setErrorMessage('');
    try {
      const data = await calendarMutation.mutateAsync({
        run_async: runAsync,
        sync_subject_details: syncSubjectDetails,
      });
      setResult({ kind: 'calendar', title: t('admin.calendarSync'), data });
      setJobPage(1);
      await refreshStatus();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    }
  }

  async function handleIncrementalSync() {
    setErrorMessage('');
    const parsedBatchSize = parseIntegerParam(batchSize, { min: 1, max: 100_000 });
    if (!parsedBatchSize) {
      setErrorMessage(t('admin.invalidBatchSize'));
      return;
    }

    try {
      const data = await incrementalMutation.mutateAsync({
        run_async: runAsync,
        batch_size: parsedBatchSize,
        ...(taskName ? { task_name: taskName } : {}),
      });
      setResult({ kind: 'incremental', title: t('admin.incrementalSync'), data });
      setJobPage(1);
      await refreshStatus();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    }
  }

  const isPending = syncBangumiMutation.isPending || calendarMutation.isPending || incrementalMutation.isPending;
  const jobTotalPages = jobsQuery.data
    ? Math.max(1, Math.ceil(jobsQuery.data.count / jobPageSize))
    : Math.max(1, jobPage);

  useEffect(() => {
    if (jobsQuery.data && jobPage > jobTotalPages) setJobPage(jobTotalPages);
  }, [jobPage, jobTotalPages, jobsQuery.data]);

  return (
    <Page description={t('admin.syncDescription')} eyebrow={t('nav.groupMore')} title={t('admin.title')} width="wide">
      <div className="grid min-w-0 gap-5" data-slot="admin-workspace">
        <section
          aria-labelledby="admin-sync-console-title"
          className="overflow-hidden rounded-sm border border-border bg-surface"
          data-slot="admin-sync-console"
        >
          <header
            className="flex min-w-0 flex-wrap items-center justify-between gap-3 border-b border-border-subtle px-4 py-3"
            data-slot="admin-console-header"
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <span
                aria-hidden="true"
                className="grid size-7 shrink-0 place-items-center rounded-sm bg-[var(--ui-accent-soft)] text-[var(--ui-accent-text)]"
              >
                <DatabaseZap className="size-4" />
              </span>
              <div className="min-w-0">
                <h2 className="m-0 text-sm font-semibold leading-5 text-foreground" id="admin-sync-console-title">
                  {t('admin.syncTitle')}
                </h2>
                <p className="m-0 hidden truncate text-xs leading-5 text-muted-foreground sm:block">
                  {t('admin.syncDescription')}
                </p>
              </div>
            </div>
            <CheckboxField checked={runAsync} onCheckedChange={setRunAsync}>
              {t('admin.runAsync')}
            </CheckboxField>
          </header>

          {errorMessage ? (
            <p
              className="border-b border-[color-mix(in_srgb,var(--ui-danger)_26%,var(--ui-border))] bg-[var(--ui-danger-soft)] px-4 py-2 text-xs font-medium leading-5 text-[var(--ui-danger-text)]"
              data-slot="admin-console-error"
              role="alert"
            >
              {errorMessage}
            </p>
          ) : null}

          <div
            className="grid min-w-0 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.42fr)]"
            data-slot="admin-console-body"
          >
            <div className="min-w-0 divide-y divide-border-subtle" data-slot="admin-sync-commands">
              <form
                className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end"
                data-slot="admin-subject-command"
                onSubmit={(event) => void handleBangumiSync(event)}
              >
                <Field>
                  <FieldLabel>{t('admin.bangumiSubject')}</FieldLabel>
                  <Input
                    inputMode="numeric"
                    placeholder={t('admin.bangumiPlaceholder')}
                    value={bangumiId}
                    onChange={(event) => {
                      setBangumiId(event.target.value);
                    }}
                  />
                </Field>
                <Button className="sm:self-end" disabled={isPending} type="submit" variant="accent">
                  <DatabaseZap className="size-4" />
                  {runAsync ? t('admin.queueSync') : t('admin.syncNow')}
                </Button>
              </form>

              <div
                className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
                data-slot="admin-calendar-command"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <CalendarDays aria-hidden="true" className="size-4 text-subtle-foreground" />
                    <h3 className="m-0 text-[13px] font-medium leading-5 text-foreground">{t('admin.calendarSync')}</h3>
                  </div>
                  <CheckboxField className="mt-2" checked={syncSubjectDetails} onCheckedChange={setSyncSubjectDetails}>
                    {t('admin.syncDetails')}
                  </CheckboxField>
                </div>
                <Button
                  className="sm:self-center"
                  disabled={isPending}
                  type="button"
                  variant="secondary"
                  onClick={() => void handleCalendarSync()}
                >
                  <CalendarDays className="size-4" />
                  {runAsync ? t('admin.queueSync') : t('admin.syncNow')}
                </Button>
              </div>

              <div className="grid gap-3 p-4" data-slot="admin-incremental-command">
                <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2">
                    <Activity aria-hidden="true" className="size-4 shrink-0 text-subtle-foreground" />
                    <h3 className="m-0 truncate text-[13px] font-medium leading-5 text-foreground">
                      {t('admin.incrementalSync')}
                    </h3>
                  </div>
                  <Button
                    disabled={isPending}
                    type="button"
                    variant="secondary"
                    onClick={() => void handleIncrementalSync()}
                  >
                    <Activity className="size-4" />
                    {runAsync ? t('admin.queueSync') : t('admin.syncNow')}
                  </Button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="grid gap-2" data-slot="admin-task-type-field">
                    <span className="text-[13px] font-medium leading-5 text-foreground">{t('admin.taskName')}</span>
                    <FilterMenu
                      label={t('admin.taskName')}
                      options={incrementalTaskValues.map((option) => ({
                        label: option || t('admin.allTasks'),
                        value: option,
                      }))}
                      value={taskName}
                      onChange={setTaskName}
                    />
                  </div>
                  <Field>
                    <FieldLabel>{t('admin.batchSize')}</FieldLabel>
                    <Input
                      inputMode="numeric"
                      max={100_000}
                      min={1}
                      type="number"
                      value={batchSize}
                      onChange={(event) => {
                        setBatchSize(event.target.value);
                      }}
                    />
                  </Field>
                </div>
              </div>
            </div>

            <aside
              aria-labelledby="admin-last-result-title"
              className="min-w-0 border-t border-border-subtle bg-muted/35 lg:border-l lg:border-t-0"
              data-slot="admin-result-aside"
            >
              <div className="border-b border-border-subtle px-4 py-3">
                <h2 className="m-0 text-sm font-semibold leading-5 text-foreground" id="admin-last-result-title">
                  {t('admin.lastResult')}
                </h2>
              </div>
              <div className="p-4">
                <AdminResultPanel result={result} />
              </div>
            </aside>
          </div>
        </section>

        <AdminSyncJobList
          currentPage={jobPage}
          isRefreshing={jobsQuery.isFetching}
          jobs={jobsQuery.data?.results ?? []}
          onRefresh={() => void refreshStatus()}
          onPageChange={setJobPage}
          totalPages={jobTotalPages}
        />

        <section
          aria-labelledby="admin-status-title"
          className="grid min-w-0 gap-3 border-t border-border-subtle pt-5"
          data-slot="admin-status"
        >
          <header>
            <h2 className="m-0 text-sm font-semibold leading-5 text-foreground" id="admin-status-title">
              {t('admin.statusTitle')}
            </h2>
            <p className="m-0 mt-0.5 text-xs leading-5 text-muted-foreground">{t('admin.statusDescription')}</p>
          </header>
          {statusQuery.isLoading ? <LoadingState title={t('common.loading')} /> : null}
          {statusQuery.isError ? (
            <ErrorState description={t('search.errorBody')} title={t('search.errorTitle')} />
          ) : null}
          {statusQuery.data ? <AdminStatusList tasks={statusQuery.data.tasks} /> : null}
        </section>
      </div>
    </Page>
  );
}
