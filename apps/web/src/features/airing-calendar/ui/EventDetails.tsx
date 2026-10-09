import { useEffect, type ReactNode } from 'react';
import { Link } from '@tanstack/react-router';
import { Clock, Tag, X } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';
import { CoverImage } from '@/shared/ui/CoverImage';
import { formatDayTitle, formatTime, titleOf, weekdayName, type CalendarOccurrence } from '../model/calendar';
import { Button } from '@/shared/ui/Button';

/**
 * Google Calendar style detail card: accent anchor, the work title, and the
 * supporting facts as icon rows.
 */
export function EventDetails({
  occurrence,
  onClose,
  state,
}: {
  occurrence: CalendarOccurrence;
  onClose: () => void;
  state: RouteBackState;
}) {
  const { locale, t } = useI18n();
  const entry = occurrence.entry;
  const work = entry.work;
  const time = formatTime(occurrence.startMinutes, locale);
  const end =
    occurrence.startMinutes === null ? '' : formatTime(occurrence.startMinutes + occurrence.durationMinutes, locale);
  const weekday = entry.weekday === null ? '' : weekdayName(locale, entry.weekday);
  const timeText = time
    ? `${weekday ? `${weekday} ` : ''}${time}${end ? ` – ${end}` : ''}`
    : weekday
      ? `${t('calendar.everyWeek')}${weekday}`
      : t('calendar.unscheduled');

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/20 p-0 sm:items-center sm:p-6"
      onClick={onClose}
      role="presentation"
    >
      <div
        aria-label={t('calendar.detailTitle')}
        aria-modal
        className="w-full max-w-[420px] rounded-t-[24px] border border-[var(--ui-border)] bg-[var(--ui-bg-inset)] p-5 shadow-[var(--ui-shadow-popup)] sm:rounded-[24px]"
        onClick={(event) => {
          event.stopPropagation();
        }}
        role="dialog"
      >
        <div className="flex items-start justify-end">
          <Button
            aria-label={t('calendar.detailClose')}
            onClick={onClose}
            size="icon"
            tooltip={t('calendar.detailClose')}
            variant="ghost"
          >
            <X className="size-4" />
          </Button>
        </div>

        <div className="mt-1 flex items-start gap-3">
          <span className="calendar-dot mt-2 size-3.5 shrink-0 rounded-[4px]" />
          <span className="min-w-0">
            <span className="line-clamp-2 block text-[20px] font-semibold leading-snug text-[var(--ui-text)]">
              {titleOf(occurrence)}
            </span>
            <span className="mt-1 block text-[13px] text-[var(--ui-text-muted)]">
              {formatDayTitle(occurrence.date, locale)}
            </span>
          </span>
        </div>

        <dl className="mt-5 grid gap-1">
          <DetailRow icon={<Clock className="size-4" />} value={timeText} />
          {entry.format ? <DetailRow icon={<Tag className="size-4" />} value={entry.format} /> : null}
        </dl>

        {work ? (
          <div className="mt-4 flex items-center gap-3 border-t border-[var(--ui-border-subtle)] pt-4">
            <CoverImage
              alt=""
              className="h-14 w-11 shrink-0 rounded-sm bg-[var(--ui-bg-subtle)] object-cover"
              label={work.displayName}
              seed={work.id}
              src={work.cover}
            />
            <Link
              className="text-sm font-medium text-[var(--ui-accent-text)] hover:underline"
              state={state}
              to={routes.entity(work.id)}
            >
              {t('calendar.openWork')}
            </Link>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function DetailRow({ icon, value }: { icon: ReactNode; value: string }) {
  return (
    <div className="flex items-center gap-3 py-1.5 text-[14px] text-[var(--ui-text)]">
      <span className="grid size-5 shrink-0 place-items-center text-[var(--ui-text-muted)]">{icon}</span>
      <span className="min-w-0 truncate">{value}</span>
    </div>
  );
}
