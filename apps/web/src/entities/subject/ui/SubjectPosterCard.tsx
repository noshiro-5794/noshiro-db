import { Link } from '@tanstack/react-router';
import type { RouteBackState } from '@/shared/routing/route-state';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { CoverImage } from '@/shared/ui/CoverImage';

type SubjectPosterCardProps = {
  /** Optional overlay, used by the catalogue for the engagement badge. */
  badge?: string | undefined;
  poster: string | null | undefined;
  seed?: string | undefined;
  state?: RouteBackState | undefined;
  subtitle?: string | undefined;
  title: string;
  to: string;
};

/**
 * The poster tile every list of works is built from - the catalogue grid and
 * the landing showcase alike. Artwork falls back to a generated cover, so a
 * missing poster never leaves a grey hole in the grid.
 */
export function SubjectPosterCard({ badge, poster, seed, state, subtitle, title, to }: SubjectPosterCardProps) {
  return (
    <Link
      className="group grid min-w-0 gap-2"
      data-slot="subject-poster"
      {...(state === undefined ? {} : { state })}
      {...resolvedRouteHref(to)}
    >
      <div className="relative aspect-[2/3] overflow-hidden rounded-[var(--ui-radius-surface)] bg-[var(--ui-bg-subtle)] ring-1 ring-[var(--ui-border)] transition-colors group-hover:bg-[var(--ui-bg-muted)] group-hover:ring-[var(--ui-border-strong)]">
        <CoverImage alt={title} className="size-full object-cover" label={title} seed={seed} src={poster} />
        {badge ? (
          <span className="absolute left-2 top-2 rounded-full bg-black/55 px-2 py-1 text-[11px] font-semibold text-white backdrop-blur">
            {badge}
          </span>
        ) : null}
      </div>
      <span className="min-w-0">
        <span className="line-clamp-2 text-sm font-semibold leading-5 text-[var(--ui-text)]">{title}</span>
        {subtitle ? (
          <span className="mt-1 block min-w-0 truncate text-xs text-[var(--ui-text-muted)]">{subtitle}</span>
        ) : null}
      </span>
    </Link>
  );
}
