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
    <Page eyebrow={t('nav.groupDiscover')} seo={false} title={t('nav.broadcastBoard')} width="wide">
      <Seo description={t('nav.broadcastBoardBody')} path={routes.airing} title={t('nav.broadcastBoard')} />
      <div className="grid gap-4 pb-10">
        <div className="flex items-baseline gap-3">
          <h1 className="text-[28px] font-semibold tracking-tight text-[var(--ui-text)]">{t('nav.broadcastBoard')}</h1>
          <span className="text-xs tabular-nums text-[var(--ui-text-muted)]">
            {`${entries.length} ${t('calendar.itemsUnit')}`}
          </span>
        </div>
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
