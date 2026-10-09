import type { ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

/**
 * Visitor-facing page heading.
 *
 * The workspace keeps its compact sticky context bar, but a public page opens
 * the way Linear's pages do: a small eyebrow above a large title, an optional
 * one-line description, and any controls aligned to the baseline.
 */
export function PageHeading({
  actions,
  className,
  description,
  eyebrow,
  meta,
  title,
}: {
  actions?: ReactNode;
  className?: string;
  description?: string | undefined;
  eyebrow?: string | undefined;
  meta?: ReactNode;
  title: string;
}) {
  return (
    <header className={cn('grid gap-3 pb-5', className)}>
      {eyebrow ? <p className="text-[12px] font-medium text-[var(--ui-text-subtle)]">{eyebrow}</p> : null}
      <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
        <div className="grid min-w-0 gap-1.5">
          <h1 className="text-[26px] font-semibold leading-tight tracking-tight text-[var(--ui-text)] sm:text-[30px]">
            {title}
          </h1>
          {description ? (
            <p className="max-w-[720px] text-[13.5px] leading-6 text-[var(--ui-text-muted)]">{description}</p>
          ) : null}
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {meta ? (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[12px] text-[var(--ui-text-subtle)]">
          {meta}
        </div>
      ) : null}
    </header>
  );
}
