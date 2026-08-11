import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { Link } from '@tanstack/react-router';
import { Star } from 'lucide-react';
import type { UserSubject } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { formatDate } from '@/shared/lib/date';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';
import { Badge } from '@/shared/ui/Badge';

const coverPlaceholder = placeholderImagePaths.subjectCover;

function titleOf(item: UserSubject, fallback: string) {
  return item.subject.display_title || item.subject.title || item.subject.title_cn || fallback;
}

function metadataOf(item: UserSubject, episodeUnit: string) {
  const { subject } = item;
  const year = subject.year ?? subject.date?.slice(0, 4);
  const episodes =
    typeof subject.content?.episodes === 'number' && subject.content.episodes > 0
      ? `${subject.content.episodes} ${episodeUnit}`
      : '';
  const hasSubtitle = Boolean(subject.display_subtitle);

  return [
    subject.subject_type,
    subject.platform || '',
    !hasSubtitle && year ? String(year) : '',
    !hasSubtitle ? episodes : '',
  ]
    .filter(Boolean)
    .filter((value, index, values) => values.indexOf(value) === index)
    .slice(0, 4);
}

function subtitleOf(item: UserSubject) {
  const { subject } = item;
  return (
    subject.display_subtitle ||
    subject.display_meta?.join(' / ') ||
    subject.date ||
    subject.platform ||
    subject.subject_type ||
    ''
  );
}

function statusLabel(status: string, t: ReturnType<typeof useI18n>['t']) {
  const labels: Record<string, string> = {
    wish: t('status.wish'),
    doing: t('status.doing'),
    done: t('status.done'),
    on_hold: t('status.onHold'),
    drop: t('status.drop'),
  };
  return labels[status] ?? status.replaceAll('_', ' ');
}

function SimpleRating({ value }: { value: number | null }) {
  const { t } = useI18n();
  if (!value) return <span className="text-sm text-[var(--ui-text-subtle)]">{t('library.noSimpleRating')}</span>;

  return (
    <span aria-label={`${t('library.simpleRatingLabel')} ${value}/5`} className="flex items-center gap-0.5">
      {Array.from({ length: 5 }, (_, index) => (
        <Star
          className={
            index < value
              ? 'size-4 fill-[var(--ui-accent)] text-[var(--ui-accent)]'
              : 'size-4 text-[var(--ui-border-strong)]'
          }
          key={index}
        />
      ))}
    </span>
  );
}

export function UserSubjectListItem({
  detailLinkState,
  item,
  showWatchDates = false,
}: {
  detailLinkState?: RouteBackState;
  item: UserSubject;
  showWatchDates?: boolean;
}) {
  const { t } = useI18n();

  return (
    <Link
      className="grid min-w-0 grid-cols-[56px_minmax(0,1fr)_auto] gap-3 border-b border-border-subtle p-3 transition-colors last:border-b-0 hover:bg-muted max-sm:grid-cols-[48px_minmax(0,1fr)] max-sm:gap-2.5"
      data-slot="user-subject-row"
      to={routes.subject(item.subject.id)}
      {...(detailLinkState === undefined ? {} : { state: detailLinkState })}
    >
      <img
        alt=""
        className="h-[78px] w-14 rounded-[var(--ui-radius-control)] bg-[var(--ui-bg-subtle)] object-cover ring-1 ring-[var(--ui-border)] max-sm:h-[68px] max-sm:w-12"
        decoding="async"
        loading="lazy"
        referrerPolicy="no-referrer"
        src={item.subject.image_thumbnail || item.subject.image || coverPlaceholder}
      />
      <span className="grid min-w-0 content-center gap-1.5">
        <span className="grid min-w-0 gap-1">
          <span className="line-clamp-1 font-semibold text-[var(--ui-text)]">
            {titleOf(item, t('common.untitledSubject'))}
          </span>
          {subtitleOf(item) ? (
            <span className="line-clamp-1 text-sm text-[var(--ui-text-muted)]">{subtitleOf(item)}</span>
          ) : null}
        </span>
        <span className="flex min-w-0 flex-wrap gap-1.5">
          {metadataOf(item, t('common.episodeUnit')).map((metadata) => (
            <span
              className="rounded-[var(--ui-radius-control)] bg-[var(--ui-bg-subtle)] px-1.5 py-0.5 text-[11px] font-medium text-[var(--ui-text-muted)]"
              key={metadata}
            >
              {metadata}
            </span>
          ))}
        </span>
        {item.comment ? (
          <span className="line-clamp-1 text-sm font-medium text-[var(--ui-text-muted)]">{item.comment}</span>
        ) : item.subject.description_excerpt ? (
          <span className="line-clamp-1 text-sm leading-6 text-[var(--ui-text-muted)]">
            {item.subject.description_excerpt}
          </span>
        ) : null}
        {showWatchDates && (item.watch_start_date || item.watch_end_date) ? (
          <span className="text-xs text-[var(--ui-text-subtle)]">
            {[
              item.watch_start_date ? `${t('library.started')} ${formatDate(item.watch_start_date)}` : '',
              item.watch_end_date ? `${t('library.finished')} ${formatDate(item.watch_end_date)}` : '',
            ]
              .filter(Boolean)
              .join(' · ')}
          </span>
        ) : null}
      </span>
      <span className="grid justify-items-end gap-2 self-center max-sm:col-start-2 max-sm:justify-items-start">
        <Badge variant="secondary">{statusLabel(item.status, t)}</Badge>
        <span className="grid justify-items-end gap-1 text-sm text-[var(--ui-text-muted)] max-sm:justify-items-start">
          {item.rating ? <strong className="font-semibold text-[var(--ui-text)]">{item.rating}</strong> : null}
          <SimpleRating value={item.simple_rating} />
        </span>
        {item.updated_at ? (
          <span className="text-xs text-[var(--ui-text-subtle)]">{formatDate(item.updated_at)}</span>
        ) : null}
      </span>
    </Link>
  );
}
