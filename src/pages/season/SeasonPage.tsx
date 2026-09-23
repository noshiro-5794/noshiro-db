import { useMemo } from 'react';
import { useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { subjectQueries } from '@/entities/subject';
import { SeasonTimeline } from '@/features/airing-calendar';
import { useI18n } from '@/shared/i18n';
import { routeBackState } from '@/shared/routing/route-state';
import { routes } from '@/shared/routing/paths';
import { Seo } from '@/shared/seo/Seo';
import { Page } from '@/shared/ui/Page';
import { ResultsState, type ResultsStatus } from '@/shared/ui/DataView';

/**
 * Season module: the quarter as a timeline, one bar per work spanning its run.
 */
export function SeasonPage() {
  const { t } = useI18n();
  const location = useLocation();
  const boardQuery = useQuery(subjectQueries.calendarBoard());
  const entries = useMemo(() => boardQuery.data ?? [], [boardQuery.data]);
  const subjectLinkState = useMemo(() => routeBackState(location, t('nav.season')), [location, t]);

  const status: ResultsStatus =
    boardQuery.data === undefined && boardQuery.isLoading
      ? 'loading'
      : boardQuery.data === undefined && boardQuery.isError
        ? 'error'
        : entries.length === 0
          ? 'empty'
          : 'ready';

  return (
    <Page eyebrow={t('nav.groupDiscover')} seo={false} title={t('nav.season')} width="wide">
      <Seo description={t('nav.seasonBody')} path={routes.season} title={t('nav.season')} />
      <div className="grid gap-4 pb-10">
        <div className="grid gap-1">
          <h1 className="text-[28px] font-semibold tracking-tight text-[var(--ui-text)]">{t('nav.season')}</h1>
          <p className="text-[13px] text-[var(--ui-text-muted)]">{t('nav.seasonBody')}</p>
        </div>
        <ResultsState
          emptyTitle={t('calendar.empty')}
          errorDescription={t('calendar.errorBody')}
          errorTitle={t('calendar.errorTitle')}
          loadingTitle={t('calendar.loading')}
          status={status}
        >
          <SeasonTimeline entries={entries} state={subjectLinkState} />
        </ResultsState>
      </div>
    </Page>
  );
}
