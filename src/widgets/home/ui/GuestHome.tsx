import { useMemo } from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight } from 'lucide-react';
import { subjectQueries } from '@/entities/subject';
import { useI18n } from '@/shared/i18n';
import { routeBackState } from '@/shared/routing/route-state';
import { routes } from '@/shared/routing/paths';
import '@/shared/ui/motion.css';
import { BroadcastBoard } from '@/features/airing-calendar';
import { SearchShowcase } from './SearchShowcase';

/**
 * Public landing page.
 *
 * Structure follows Linear's marketing page — a large left-aligned headline, a
 * framed preview of the real product, a thin data bar, a statement, and a
 * three-column figure grid — but every surface is drawn with the app's own
 * tokens so the page reads correctly in both light and dark themes.
 */
export function GuestHome() {
  const { t } = useI18n();
  const location = useLocation();
  const boardQuery = useQuery(subjectQueries.calendarBoard());
  const entries = useMemo(() => boardQuery.data ?? [], [boardQuery.data]);
  const subjectLinkState = useMemo(() => routeBackState(location, t('calendar.title')), [location, t]);
  const sourceCount = useMemo(
    () => new Set(entries.flatMap((entry) => entry.sources.map((source) => source.provider))).size,
    [entries],
  );

  return (
    <div className="pb-16">
      <section className="mx-auto max-w-[1160px] px-4 pb-10 pt-14 sm:pt-20">
        <p className="motion-rise text-[13px] font-medium text-[var(--ui-text-subtle)]">{t('public.tagline')}</p>
        <h1 className="motion-rise motion-delay-1 mt-4 max-w-[820px] text-[34px] font-semibold leading-[1.18] tracking-tight text-[var(--ui-text)] sm:text-[46px]">
          {t('public.heroTitle')}
        </h1>
        <div className="motion-rise motion-delay-2 mt-8 flex flex-wrap items-end justify-between gap-4 border-t border-[var(--ui-border-subtle)] pt-5">
          <p className="max-w-[560px] text-[15px] leading-7 text-[var(--ui-text-muted)]">{t('public.heroBody')}</p>
          <Link
            className="inline-flex items-center gap-1.5 text-[14px] font-medium text-[var(--ui-text-muted)] transition-colors hover:text-[var(--ui-text)]"
            to={routes.calendar}
          >
            {t('public.browseSeason')}
            <ArrowRight className="size-4" />
          </Link>
        </div>
      </section>

      <section className="motion-rise motion-delay-3 mx-auto max-w-[1160px] px-4">
        <div className="overflow-hidden rounded-[14px] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] shadow-[var(--ui-shadow-surface)]">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--ui-border-subtle)] px-4 py-2.5">
            <span className="text-[12px] font-medium text-[var(--ui-text)]">{t('public.boardPreview')}</span>
            <span className="flex items-center gap-2 text-[11px] text-[var(--ui-text-subtle)]">
              <span className="size-1.5 rounded-full bg-[var(--ui-success)]" />
              {t('public.boardPreviewNote')}
            </span>
          </div>
          <div className="relative max-h-[560px] overflow-hidden px-3 py-3">
            {boardQuery.isLoading ? (
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
            ) : (
              <BroadcastBoard emptyLabel={t('calendar.empty')} entries={entries} state={subjectLinkState} />
            )}
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[var(--ui-bg-surface)] to-transparent" />
          </div>
        </div>
      </section>

      <section className="mx-auto mt-14 max-w-[1160px] px-4">
        <dl className="grid gap-6 border-y border-[var(--ui-border-subtle)] py-6 sm:grid-cols-3">
          <Stat label={t('public.statSources')} value={sourceCount > 0 ? String(sourceCount) : '—'} />
          <Stat label={t('public.statWorks')} value={entries.length > 0 ? String(entries.length) : '—'} />
          <Stat label={t('public.statRefresh')} value={t('public.statRefreshValue')} />
        </dl>
      </section>

      <section className="mx-auto mt-14 max-w-[1160px] px-4">
        <p className="max-w-[760px] text-[15px] leading-7 text-[var(--ui-text-muted)]">{t('public.statement')}</p>
      </section>

      <section className="mx-auto mt-16 grid max-w-[1160px] gap-10 px-4 md:grid-cols-3">
        <Figure body={t('public.figOneBody')} index={1} title={t('public.figOneTitle')} variant="merge" />
        <Figure body={t('public.figTwoBody')} index={2} title={t('public.figTwoTitle')} variant="calendar" />
        <Figure body={t('public.figThreeBody')} index={3} title={t('public.figThreeTitle')} variant="layers" />
      </section>

      <div className="mt-16">
        <SearchShowcase />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1.5">
      <dt className="text-[12px] text-[var(--ui-text-subtle)]">{label}</dt>
      <dd className="text-[26px] font-semibold tabular-nums leading-none text-[var(--ui-text)]">{value}</dd>
    </div>
  );
}

/**
 * Linear labels its illustrations "Fig 0.x" and draws them as thin monochrome
 * outlines. These are the same idea in plain SVG, so they inherit the theme.
 */
function Figure({
  body,
  index,
  title,
  variant,
}: {
  body: string;
  index: number;
  title: string;
  variant: 'merge' | 'calendar' | 'layers';
}) {
  return (
    <article className="grid content-start gap-4 border-t border-[var(--ui-border-subtle)] pt-5">
      <span className="text-[11px] tabular-nums text-[var(--ui-text-subtle)]">{`Fig 0.${index}`}</span>
      <FigureArt variant={variant} />
      <h3 className="text-[15px] font-medium text-[var(--ui-text)]">{title}</h3>
      <p className="text-[13px] leading-6 text-[var(--ui-text-muted)]">{body}</p>
    </article>
  );
}

function FigureArt({ variant }: { variant: 'merge' | 'calendar' | 'layers' }) {
  const stroke = 'var(--ui-border-strong)';
  return (
    <svg
      aria-hidden
      className="h-[132px] w-full"
      fill="none"
      preserveAspectRatio="xMidYMid meet"
      stroke={stroke}
      strokeWidth="1"
      viewBox="0 0 200 132"
    >
      {variant === 'merge' ? (
        <>
          <path d="M20 30h48l16 16" />
          <path d="M20 66h48l16-20" />
          <path d="M20 102h48l16 16" />
          <rect height="24" rx="4" width="42" x="14" y="18" />
          <rect height="24" rx="4" width="42" x="14" y="54" />
          <rect height="24" rx="4" width="42" x="14" y="90" />
          <rect height="34" rx="6" width="52" x="112" y="49" />
          <path d="M164 66h22" />
          <path d="M180 60l8 6-8 6" />
        </>
      ) : null}
      {variant === 'calendar' ? (
        <>
          <rect height="86" rx="6" width="164" x="18" y="22" />
          <path d="M18 46h164" />
          <path d="M59 22v86M100 22v86M141 22v86" />
          <path d="M18 65h164M18 84h164" />
          <rect height="12" rx="3" width="24" x="30" y="52" fill={stroke} stroke="none" opacity="0.5" />
          <rect height="12" rx="3" width="24" x="112" y="52" fill={stroke} stroke="none" opacity="0.3" />
          <rect height="12" rx="3" width="24" x="71" y="90" fill={stroke} stroke="none" opacity="0.4" />
        </>
      ) : null}
      {variant === 'layers' ? (
        <>
          <path d="M100 18l56 30-56 30-56-30z" />
          <path d="M44 78l56 30 56-30" />
          <path d="M44 96l56 30 56-30" />
        </>
      ) : null}
    </svg>
  );
}

export function SessionCheckingHome() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="h-44 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)] sm:col-span-2" />
      <div className="h-44 rounded-lg border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)]" />
    </div>
  );
}
