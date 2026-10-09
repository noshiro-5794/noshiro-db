import { useMemo } from 'react';
import { useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { subjectQueries } from '@/entities/subject';
import { BroadcastBoard } from '@/features/airing-calendar';
import { useI18n } from '@/shared/i18n';
import { routeBackState } from '@/shared/routing/route-state';
import { routes } from '@/shared/routing/paths';
import '@/shared/ui/motion.css';
import { LandingSection } from './LandingSection';

/**
 * The season on the landing page: the real weekly board, cropped, so a visitor
 * sees airtimes and artwork before signing up for anything.
 */
export function SeasonSpotlight() {
  const { t } = useI18n();
  const location = useLocation();
  const boardQuery = useQuery(subjectQueries.calendarBoard());
  const entries = useMemo(() => boardQuery.data ?? [], [boardQuery.data]);
  const subjectLinkState = useMemo(() => routeBackState(location, t('nav.home')), [location, t]);

  return (
    <LandingSection
      action={{ label: t('public.more'), to: routes.airing }}
      className="motion-rise motion-delay-4"
      note={t('public.seasonNote')}
      title={t('public.seasonHeading')}
    >
      <div className="overflow-hidden rounded-[var(--ui-radius-frame)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] shadow-[var(--ui-shadow-surface)]">
        <div className="relative max-h-[420px] overflow-hidden px-3 py-3">
          {boardQuery.isLoading ? (
            <BoardSkeleton />
          ) : (
            <BroadcastBoard
              emptyLabel={t('calendar.empty')}
              entries={entries}
              showProvenance={false}
              state={subjectLinkState}
            />
          )}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-[var(--ui-bg-surface)] to-transparent" />
        </div>
      </div>
    </LandingSection>
  );
}

function BoardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-2.5 md:min-w-[1000px] md:grid-cols-7">
      {Array.from({ length: 7 }, (_, column) => (
        <div className="grid content-start gap-2" key={column}>
          <div className="h-4 w-16 rounded bg-[var(--ui-bg-subtle)]" />
          {Array.from({ length: column % 2 === 0 ? 5 : 4 }, (_, row) => (
            <div className="h-[70px] rounded-[var(--ui-radius-surface)] bg-[var(--ui-bg-subtle)]" key={row} />
          ))}
        </div>
      ))}
    </div>
  );
}
