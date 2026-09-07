import { type SyntheticEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { DatabaseZap } from 'lucide-react';
import { AdminSyncJobList, syncMutations, syncQueries, syncQueryKeys } from '@/features/admin-sync';
import { useI18n } from '@/shared/i18n';
import { getErrorMessage } from '@/shared/lib/error';
import { Button } from '@/shared/ui/Button';
import { CheckboxField } from '@/shared/ui/Checkbox';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';

const jobPageSize = 8;

export function AdminPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [externalId, setExternalId] = useState('');
  const [includeRelated, setIncludeRelated] = useState(true);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [errorMessage, setErrorMessage] = useState('');
  const createMutation = useMutation(syncMutations.createImportJob());
  const jobsQuery = useQuery(
    syncQueries.importJobs({ ...(cursor === undefined ? {} : { cursor }), page_size: jobPageSize }),
  );

  function resetToFirstPage() {
    setCursor(undefined);
  }

  async function refreshJobs() {
    await queryClient.invalidateQueries({ queryKey: syncQueryKeys.importJobs() });
  }

  async function handleCreateJob(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    setErrorMessage('');
    if (!/^v[1-9][0-9]*$/u.test(externalId.trim())) {
      setErrorMessage(t('admin.invalidBangumiId'));
      return;
    }

    try {
      await createMutation.mutateAsync({
        provider: 'vndb',
        external_id: externalId.trim(),
        include_related: includeRelated,
      });
      setExternalId('');
      resetToFirstPage();
      await refreshJobs();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, t('common.requestFailed')));
    }
  }

  return (
    <Page description={t('admin.syncDescription')} eyebrow={t('nav.groupMore')} title={t('admin.title')} width="wide">
      <div className="grid min-w-0 gap-5" data-slot="admin-workspace">
        <section
          aria-labelledby="admin-import-console-title"
          className="overflow-hidden rounded-sm border border-border bg-surface"
          data-slot="admin-import-console"
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
                <h2 className="m-0 text-sm font-semibold leading-5 text-foreground" id="admin-import-console-title">
                  {t('admin.syncTitle')}
                </h2>
                <p className="m-0 hidden truncate text-xs leading-5 text-muted-foreground sm:block">
                  {t('admin.syncDescription')}
                </p>
              </div>
            </div>
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

          <form
            className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto]"
            onSubmit={(event) => void handleCreateJob(event)}
          >
            <div className="grid gap-3">
              <Field>
                <FieldLabel>VNDB ID</FieldLabel>
                <Input
                  placeholder="v17"
                  value={externalId}
                  onChange={(event) => {
                    setExternalId(event.target.value);
                  }}
                />
              </Field>
              <CheckboxField checked={includeRelated} onCheckedChange={setIncludeRelated}>
                {t('admin.syncDetails')}
              </CheckboxField>
            </div>
            <Button className="sm:self-end" disabled={createMutation.isPending} type="submit" variant="accent">
              <DatabaseZap className="size-4" />
              {createMutation.isPending ? t('common.saving') : t('admin.queueSync')}
            </Button>
          </form>
        </section>

        <AdminSyncJobList
          hasNextPage={Boolean(jobsQuery.data?.next)}
          isRefreshing={jobsQuery.isFetching}
          jobs={jobsQuery.data?.results ?? []}
          onLoadMore={() => {
            if (jobsQuery.data?.next) setCursor(jobsQuery.data.next);
          }}
          onRefresh={() => void refreshJobs()}
        />
      </div>
    </Page>
  );
}
