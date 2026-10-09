import type { ReactNode } from 'react';
import { Link } from '@tanstack/react-router';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';

type LandingSectionProps = {
  action?: { label: string; to: string };
  children: ReactNode;
  className?: string;
  note?: string;
  title?: string;
};

/**
 * Shared rhythm for the landing page: one width, one gutter, one heading pair.
 * Sections pass a title, a one-line note, and an optional link to the full page.
 */
export function LandingSection({ action, children, className, note, title }: LandingSectionProps) {
  return (
    <section className={cn('mx-auto w-full max-w-[1160px] px-4', className)}>
      {title === undefined ? null : (
        <div className="mb-5 flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
          <div className="min-w-0">
            <h2 className="text-[19px] font-semibold tracking-tight text-[var(--ui-text)]">{title}</h2>
            {note === undefined ? null : <p className="mt-1 text-[13px] text-[var(--ui-text-muted)]">{note}</p>}
          </div>
          {action === undefined ? null : (
            <Link
              className="inline-flex shrink-0 items-center gap-1 rounded-[var(--ui-radius-control)] text-[13px] font-medium text-[var(--ui-text-muted)] outline-none transition-colors hover:text-[var(--ui-text)] focus-visible:ring-2 focus-visible:ring-[var(--ui-focus)]"
              {...resolvedRouteHref(action.to)}
            >
              {action.label}
              <ArrowRight className="size-3.5" />
            </Link>
          )}
        </div>
      )}
      {children}
    </section>
  );
}
