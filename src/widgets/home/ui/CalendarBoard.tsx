import { Link, useLocation } from '@/shared/routing/navigation';
import { formatWeekday, type Locale, useI18n } from '@/shared/i18n';
import { calendarImageOf } from '@/features/search';
import type { CalendarGroup, CalendarSubjectItem, WeekdayEn } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';
import { routeBackState } from '@/shared/routing/route-state';

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;
const coverPlaceholder = '/assets/placeholders/subject-cover.png';

type CalendarBoardProps = {
  groups?: CalendarGroup[];
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
      className="group block overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-sm transition hover:-translate-y-0.5 hover:border-[var(--color-accent-border)] hover:shadow-[var(--shadow-soft)]"
      state={state}
      to={routes.subject(item.subject_id)}
    >
      <div className="relative aspect-[3/4] overflow-hidden bg-[var(--color-surface-muted)]">
        <img
          className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]"
          src={calendarImageOf(item) || coverPlaceholder}
          alt={titleOf(item, titleFallback)}
          loading="lazy"
        />
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent p-3 text-white">
          <span className="inline-flex rounded-full bg-white/15 px-2 py-1 text-[11px] font-semibold backdrop-blur">
            {formatHeat(item.doing, locale)}
          </span>
          <h3 className="mt-2 line-clamp-2 text-sm font-semibold leading-5">{titleOf(item, titleFallback)}</h3>
          {item.display_subtitle ? (
            <p className="mt-1 line-clamp-1 text-xs text-white/70">{item.display_subtitle}</p>
          ) : null}
        </div>
      </div>
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
      className="grid h-[104px] min-w-0 grid-cols-[54px_minmax(0,1fr)] gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-2.5 shadow-sm transition hover:-translate-y-0.5 hover:border-[var(--color-accent-border)] hover:shadow-[var(--shadow-soft)]"
      state={state}
      to={routes.subject(item.subject_id)}
    >
      <img
        className="h-full w-[54px] rounded-lg bg-[var(--color-surface-muted)] object-cover"
        src={calendarImageOf(item) || coverPlaceholder}
        alt={titleOf(item, titleFallback)}
        loading="lazy"
      />
      <span className="grid min-w-0 grid-rows-[auto_1fr_auto] gap-1 py-0.5">
        <span className="line-clamp-2 text-sm font-semibold leading-5 text-[var(--color-text)]">
          {titleOf(item, titleFallback)}
        </span>
        <span className="line-clamp-1 self-center text-xs text-[var(--color-text-muted)]">
          {item.display_subtitle || item.platform || item.subject_type}
        </span>
        <span className="flex min-w-0 items-center gap-2 text-xs font-medium text-[var(--color-text-muted)]">
          <span className="rounded-full bg-[var(--color-surface-muted)] px-2 py-0.5">
            {formatHeat(item.doing, locale)}
          </span>
          <span className="min-w-0 truncate">{item.subject_type}</span>
        </span>
      </span>
    </Link>
  );
}

export function CalendarBoard({ groups = [], isLoading }: CalendarBoardProps) {
  const { locale, t } = useI18n();
  const location = useLocation();
  const subjectLinkState = routeBackState(location, t('calendar.title'));

  return (
    <div className="overflow-x-auto pb-2">
      <div className="grid min-w-[1680px] grid-cols-7 gap-4">
        {weekdays.map((weekday) => {
          const items = findGroup(groups, weekday)?.items ?? [];
          const [featuredItem, ...restItems] = items;

          return (
            <section
              className="flex min-h-[580px] flex-col rounded-2xl border border-[var(--color-border)] bg-[color-mix(in_srgb,var(--color-surface-muted)_56%,transparent)] p-4"
              key={weekday}
            >
              <header className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--color-text)]">{formatWeekday(locale, weekday)}</h3>
                  <p className="text-xs text-[var(--color-text-muted)]">{weekday}</p>
                </div>
                <span className="inline-flex min-w-7 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-xs font-semibold text-[var(--color-text-muted)]">
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
                <div className="grid aspect-[3/4] place-items-center rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] text-xs text-[var(--color-text-muted)]">
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
