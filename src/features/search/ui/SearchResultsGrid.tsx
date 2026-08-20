import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { useMemo } from 'react';
import { Link } from '@tanstack/react-router';
import type { CalendarSubjectItem, SubjectSummary } from '@/shared/api';
import type { Locale } from '@/shared/i18n';
import { useI18n } from '@/shared/i18n';
import type { RouteBackState } from '@/shared/routing/route-state';
import { calendarImageOf } from '../model/calendar-search';

const coverPlaceholder = placeholderImagePaths.subjectCover;

function titleOf(item: Pick<SubjectSummary, 'display_title' | 'title' | 'title_cn'>, fallback: string) {
  return item.display_title || item.title || item.title_cn || fallback;
}

function subjectPosterOf(subject: SubjectSummary) {
  return (
    subject.images?.poster || subject.images?.thumbnail || subject.image_thumbnail || subject.image || coverPlaceholder
  );
}

function SearchPoster({
  badge,
  poster,
  state,
  subjectId,
  subtitle,
  title,
}: {
  badge?: string;
  poster: string;
  state: RouteBackState;
  subjectId: string;
  subtitle: string;
  title: string;
}) {
  return (
    <Link className="group grid min-w-0 gap-2" params={{ subjectId }} state={state} to="/entities/$subjectId">
      <div className="relative aspect-[2/3] overflow-hidden rounded-md bg-muted ring-1 ring-border transition-[background-color,box-shadow] duration-[var(--ui-transition-fast)] group-hover:bg-[var(--ui-bg-muted)] group-hover:ring-[var(--ui-border-strong)]">
        <img
          alt={title}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
          decoding="async"
          loading="lazy"
          referrerPolicy="no-referrer"
          src={poster}
        />
        {badge ? (
          <div className="absolute left-2 top-2 rounded-full bg-black/55 px-2 py-1 text-[11px] font-semibold text-white backdrop-blur">
            {badge}
          </div>
        ) : null}
      </div>
      <span className="min-w-0">
        <span className="line-clamp-2 text-sm font-semibold leading-5 text-[var(--ui-text)]">{title}</span>
        <span className="mt-1 line-clamp-1 text-xs text-[var(--ui-text-muted)]">{subtitle}</span>
      </span>
    </Link>
  );
}

export function SearchResultsGrid({
  calendarItems,
  locale,
  state,
  subjects,
  useDatabaseResults,
}: {
  calendarItems: CalendarSubjectItem[];
  locale: Locale;
  state: RouteBackState;
  subjects: SubjectSummary[];
  useDatabaseResults: boolean;
}) {
  const { t } = useI18n();
  const numberFormatters = useMemo(
    () => ({
      compact: new Intl.NumberFormat(locale, { notation: 'compact' }),
      standard: new Intl.NumberFormat(locale),
    }),
    [locale],
  );

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {useDatabaseResults
        ? subjects.map((subject) => (
            <SearchPoster
              key={subject.id}
              poster={subjectPosterOf(subject)}
              state={state}
              subjectId={subject.id}
              subtitle={subject.display_subtitle || subject.subject_type}
              title={titleOf(subject, t('common.untitledSubject'))}
            />
          ))
        : calendarItems.map((item) => (
            <SearchPoster
              badge={(item.doing >= 10_000 ? numberFormatters.compact : numberFormatters.standard).format(item.doing)}
              key={item.subject_id}
              poster={calendarImageOf(item) || coverPlaceholder}
              state={state}
              subjectId={item.subject_id}
              subtitle={item.display_subtitle || item.subject_type}
              title={titleOf(item, t('common.untitledSubject'))}
            />
          ))}
    </div>
  );
}
