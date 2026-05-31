import { Link } from 'react-router-dom';
import type { Locale } from '@/features/i18n/messages';
import { useI18n } from '@/features/i18n/use-i18n';
import type { CalendarGroup, CalendarSubjectItem, WeekdayEn } from '@/lib/api/types';
import { routes } from '@/routes/paths';

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;
const coverPlaceholder = '/assets/placeholders/subject-cover.png';

const weekdayLabels: Record<Locale, Record<WeekdayEn, string>> = {
  'zh-CN': {
    Mon: '周一',
    Tue: '周二',
    Wed: '周三',
    Thu: '周四',
    Fri: '周五',
    Sat: '周六',
    Sun: '周日',
  },
  'en-US': {
    Mon: 'Mon',
    Tue: 'Tue',
    Wed: 'Wed',
    Thu: 'Thu',
    Fri: 'Fri',
    Sat: 'Sat',
    Sun: 'Sun',
  },
  'ja-JP': {
    Mon: '月',
    Tue: '火',
    Wed: '水',
    Thu: '木',
    Fri: '金',
    Sat: '土',
    Sun: '日',
  },
};

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

function titleOf(item: CalendarSubjectItem) {
  return item.display_title || item.title || item.title_cn || 'Untitled';
}

function HeroCalendarItem({ item, locale }: { item: CalendarSubjectItem; locale: Locale }) {
  return (
    <Link
      className="group block overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-[var(--color-accent-border)] hover:shadow-md dark:border-neutral-800 dark:bg-neutral-950"
      to={routes.subject(item.subject_id)}
    >
      <div className="relative aspect-[3/4] overflow-hidden bg-neutral-100 dark:bg-neutral-900">
        <img
          className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]"
          src={item.image_thumbnail || coverPlaceholder}
          alt={titleOf(item)}
          loading="lazy"
        />
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent p-3 text-white">
          <span className="inline-flex rounded-full bg-white/15 px-2 py-1 text-[11px] font-semibold backdrop-blur">
            {formatHeat(item.doing, locale)}
          </span>
          <h3 className="mt-2 line-clamp-2 text-sm font-semibold leading-5">{titleOf(item)}</h3>
          {item.display_subtitle ? <p className="mt-1 line-clamp-1 text-xs text-white/70">{item.display_subtitle}</p> : null}
        </div>
      </div>
    </Link>
  );
}

function CompactCalendarItem({ item, locale }: { item: CalendarSubjectItem; locale: Locale }) {
  return (
    <Link
      className="grid h-[104px] min-w-0 grid-cols-[54px_minmax(0,1fr)] gap-3 rounded-xl border border-neutral-200 bg-white p-2.5 shadow-sm transition hover:-translate-y-0.5 hover:border-[var(--color-accent-border)] hover:shadow-md dark:border-neutral-800 dark:bg-neutral-950"
      to={routes.subject(item.subject_id)}
    >
      <img
        className="h-full w-[54px] rounded-lg bg-neutral-100 object-cover dark:bg-neutral-900"
        src={item.image_thumbnail || coverPlaceholder}
        alt={titleOf(item)}
        loading="lazy"
      />
      <span className="grid min-w-0 grid-rows-[auto_1fr_auto] gap-1 py-0.5">
        <span className="line-clamp-2 text-sm font-semibold leading-5 text-neutral-900 dark:text-neutral-100">{titleOf(item)}</span>
        <span className="line-clamp-1 self-center text-xs text-neutral-500 dark:text-neutral-400">
          {item.display_subtitle || item.platform || item.subject_type}
        </span>
        <span className="flex min-w-0 items-center gap-2 text-xs font-medium text-neutral-500 dark:text-neutral-400">
          <span className="rounded-full bg-neutral-100 px-2 py-0.5 dark:bg-neutral-900">{formatHeat(item.doing, locale)}</span>
          <span className="min-w-0 truncate">{item.subject_type}</span>
        </span>
      </span>
    </Link>
  );
}

export function CalendarBoard({ groups = [], isLoading }: CalendarBoardProps) {
  const { locale, t } = useI18n();

  return (
    <div className="overflow-x-auto pb-2">
      <div className="grid min-w-[1680px] grid-cols-7 gap-4">
        {weekdays.map((weekday) => {
          const items = findGroup(groups, weekday)?.items ?? [];
          const [featuredItem, ...restItems] = items;

          return (
            <section
              className="flex min-h-[580px] flex-col rounded-2xl border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-900/60"
              key={weekday}
            >
              <header className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-950 dark:text-white">{weekdayLabels[locale][weekday]}</h3>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">{weekday}</p>
                </div>
                <span className="inline-flex min-w-7 items-center justify-center rounded-full border border-neutral-200 bg-white px-2 py-1 text-xs font-semibold text-neutral-500 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-400">
                  {items.length}
                </span>
              </header>

              {featuredItem ? (
                <HeroCalendarItem item={featuredItem} locale={locale} />
              ) : (
                <div className="grid aspect-[3/4] place-items-center rounded-xl border border-dashed border-neutral-200 bg-white text-xs text-neutral-400 dark:border-neutral-800 dark:bg-neutral-950">
                  {isLoading ? t('calendar.loading') : t('calendar.empty')}
                </div>
              )}

              <div className="mt-4 grid gap-2">
                {restItems.slice(0, 4).map((item) => (
                  <CompactCalendarItem item={item} key={item.subject_id} locale={locale} />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
