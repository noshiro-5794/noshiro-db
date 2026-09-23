import { useMemo } from 'react';
import { useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { subjectQueries } from '@/entities/subject';
import { BroadcastBoard } from '@/features/airing-calendar';
import { useI18n } from '@/shared/i18n';
import { routeBackState } from '@/shared/routing/route-state';
import { routes } from '@/shared/routing/paths';
import { Seo } from '@/shared/seo/Seo';
import { Page } from '@/shared/ui/Page';
import { PageHeading } from '@/shared/ui/PageHeading';
import { ResultsState, type ResultsStatus } from '@/shared/ui/DataView';

/**
 * Broadcast board module: the season lineup arranged per weekday, so a visitor
 * can see what airs on the evening they care about.
 */
export function AiringPage() {
  const { t } = useI18n();
  const location = useLocation();
  const boardQuery = useQuery(subjectQueries.calendarBoard());
  const entries = useMemo(() => boardQuery.data ?? [], [boardQuery.data]);
  const subjectLinkState = useMemo(() => routeBackState(location, t('nav.broadcastBoard')), [location, t]);

  const status: ResultsStatus =
    boardQuery.data === undefined && boardQuery.isLoading
      ? 'loading'
      : boardQuery.data === undefined && boardQuery.isError
        ? 'error'
        : entries.length === 0
          ? 'empty'
          : 'ready';

  return (
    <Page hideHeader seo={false} title={t('nav.broadcastBoard')} width="wide">
      <Seo description={t('nav.broadcastBoardBody')} path={routes.airing} title={t('nav.broadcastBoard')} />
      <div className="grid gap-4 pb-10">
        <PageHeading
          description={t('nav.broadcastBoardBody')}
          eyebrow={t('nav.groupDiscover')}
          meta={
            <span className="tabular-nums text-[var(--ui-text-muted)]">
              {`${entries.length} ${t('calendar.itemsUnit')}`}
            </span>
          }
          title={t('nav.broadcastBoard')}
        />
        <ResultsState
          emptyTitle={t('calendar.empty')}
          errorDescription={t('calendar.errorBody')}
          errorTitle={t('calendar.errorTitle')}
          loadingTitle={t('calendar.loading')}
          status={status}
        >
          <BroadcastBoard emptyLabel={t('calendar.empty')} entries={entries} state={subjectLinkState} />
        </ResultsState>
      </div>
    </Page>
  );
}
