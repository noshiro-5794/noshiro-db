import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { Link, useLocation } from '@tanstack/react-router';
import { formatWeekday, type Locale, useI18n } from '@/shared/i18n';
import { calendarImageOf } from '@/features/search';
import type { CalendarGroup, CalendarSubjectItem, WeekdayEn } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';
import { routeBackState } from '@/shared/routing/route-state';
import { ErrorState } from '@/shared/ui/FeedbackState';

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;
const coverPlaceholder = placeholderImagePaths.subjectCover;

type CalendarBoardProps = {
  groups?: CalendarGroup[] | undefined;
  isError?: boolean;
  isLoading: boolean;
};

function findGroup(groups: CalendarGroup[], weekday: WeekdayEn) {
  return groups.find((group) => group.weekday.en === weekday);
}

function formatHeat(value: number, locale: Locale) {
  return new Intl.NumberFormat(locale, { notation: value >= 10000 ? 'compact' : 'standard' }).format(value);
}

function titleOf(item: CalendarSubjectItem, fallback: string) {
  return item.display_title || item.title || item.title_cn || fallback;
}

function HeroCalendarItem({
  item,
  locale,
  state,
  titleFallback,
}: {
  item: CalendarSubjectItem;
  locale: Locale;
  state: RouteBackState;
  titleFallback: string;
}) {
  return (
    <Link
      className="grid overflow-hidden rounded-[var(--ui-radius-surface)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] transition-colors hover:border-[var(--ui-border-strong)]"
      data-slot="calendar-featured-item"
      state={state}
      to={routes.entity(item.subject_id)}
    >
      <img
        className="aspect-[3/4] w-full bg-[var(--ui-bg-subtle)] object-cover"
        src={calendarImageOf(item) || coverPlaceholder}
        alt={titleOf(item, titleFallback)}
        decoding="async"
        loading="lazy"
        referrerPolicy="no-referrer"
      />
      <span className="grid min-w-0 gap-1.5 border-t border-[var(--ui-border-subtle)] p-3">
        <span className="line-clamp-2 text-sm font-semibold leading-5 text-[var(--ui-text)]">
          {titleOf(item, titleFallback)}
        </span>
        <span className="flex min-w-0 items-center justify-between gap-2 text-xs text-[var(--ui-text-muted)]">
          <span className="truncate">{item.display_subtitle || item.subject_type}</span>
          <span className="shrink-0 font-medium tabular-nums">{formatHeat(item.doing, locale)}</span>
        </span>
      </span>
    </Link>
  );
}

function CompactCalendarItem({
  item,
  locale,
  state,
  titleFallback,
}: {
  item: CalendarSubjectItem;
  locale: Locale;
  state: RouteBackState;
  titleFallback: string;
}) {
  return (
    <Link
      className="grid h-24 min-w-0 grid-cols-[50px_minmax(0,1fr)] gap-2.5 rounded-[var(--ui-radius-control)] border border-transparent p-2 transition-colors hover:border-[var(--ui-border-subtle)] hover:bg-[var(--ui-bg-surface)]"
      data-slot="calendar-compact-item"
      state={state}
      to={routes.entity(item.subject_id)}
    >
      <img
        className="h-full w-[50px] rounded-[var(--ui-radius-control)] bg-[var(--ui-bg-subtle)] object-cover"
        src={calendarImageOf(item) || coverPlaceholder}
        alt={titleOf(item, titleFallback)}
        decoding="async"
        loading="lazy"
        referrerPolicy="no-referrer"
      />
      <span className="grid min-w-0 grid-rows-[auto_1fr_auto] gap-1 py-0.5">
        <span className="line-clamp-2 text-sm font-semibold leading-5 text-[var(--ui-text)]">
          {titleOf(item, titleFallback)}
        </span>
        <span className="line-clamp-1 self-center text-xs text-[var(--ui-text-muted)]">
          {item.display_subtitle || item.platform || item.subject_type}
        </span>
        <span className="flex min-w-0 items-center gap-2 text-xs font-medium text-[var(--ui-text-muted)]">
          <span className="tabular-nums">{formatHeat(item.doing, locale)}</span>
          <span aria-hidden="true" className="text-[var(--ui-border-strong)]">
            /
          </span>
          <span className="min-w-0 truncate">{item.subject_type}</span>
        </span>
      </span>
    </Link>
  );
}

export function CalendarBoard({ groups = [], isError = false, isLoading }: CalendarBoardProps) {
  const { locale, t } = useI18n();
  const location = useLocation();
  const subjectLinkState = routeBackState(location, t('calendar.title'));

  if (isError) {
    return <ErrorState title={t('calendar.errorTitle')} description={t('calendar.errorBody')} />;
  }

  return (
    <div className="overflow-x-auto pb-2" data-slot="calendar-board">
      <div className="grid min-w-[1540px] grid-cols-7 gap-3">
        {weekdays.map((weekday) => {
          const items = findGroup(groups, weekday)?.items ?? [];
          const [featuredItem, ...restItems] = items;

          return (
            <section
              className="flex min-h-[540px] flex-col rounded-[var(--ui-radius-surface)] border border-[var(--ui-border)] bg-[var(--ui-bg-inset)] p-3"
              data-slot="calendar-day"
              key={weekday}
            >
              <header className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--ui-text)]">{formatWeekday(locale, weekday)}</h3>
                  <p className="text-xs text-[var(--ui-text-muted)]">{weekday}</p>
                </div>
                <span className="inline-flex min-w-7 items-center justify-center rounded-[var(--ui-radius-control)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] px-1.5 py-0.5 text-xs font-medium text-[var(--ui-text-muted)]">
                  {items.length}
                </span>
              </header>

              {featuredItem ? (
                <HeroCalendarItem
                  item={featuredItem}
                  locale={locale}
                  state={subjectLinkState}
                  titleFallback={t('common.untitledSubject')}
                />
              ) : (
                <div className="grid aspect-[3/4] place-items-center rounded-[var(--ui-radius-surface)] border border-dashed border-[var(--ui-border)] bg-[var(--ui-bg-surface)] text-xs text-[var(--ui-text-muted)]">
                  {isLoading ? t('calendar.loading') : t('calendar.empty')}
                </div>
              )}

              <div className="mt-4 grid gap-2">
                {restItems.slice(0, 4).map((item) => (
                  <CompactCalendarItem
                    item={item}
                    key={item.subject_id}
                    locale={locale}
                    state={subjectLinkState}
                    titleFallback={t('common.untitledSubject')}
                  />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
