import type { ReactNode } from 'react';
import { Link } from '@tanstack/react-router';
import { ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';
import { cn } from '@/shared/lib/cn';
import { revealVariants, revealViewport } from '@/shared/lib/motion';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';

type LandingSectionProps = {
  action?: { label: string; to: string };
  children: ReactNode;
  className?: string;
  /** A short label that sits above the heading in a hairline pill. */
  eyebrow?: string;
  note?: string;
  title?: string;
};

/**
 * One band of the landing page.
 *
 * plane's rhythm: every band shares one width and one gutter, and its intro is a
 * centred column — an optional letterspaced eyebrow, a balanced heading, one
 * line of body copy and, when the section continues elsewhere, a single link
 * beneath it. The band reveals itself the first time it scrolls into view.
 */
export function LandingSection({ action, children, className, eyebrow, note, title }: LandingSectionProps) {
  return (
    <motion.section
      className={cn('mx-auto w-full max-w-[1160px] px-4', className)}
      initial="hidden"
      variants={revealVariants}
      viewport={revealViewport}
      whileInView="visible"
    >
      {title === undefined ? null : (
        <header className="mx-auto max-w-2xl text-center">
          {eyebrow === undefined ? null : (
            <p className="text-[13px] font-semibold uppercase tracking-[0.08em] text-[var(--ui-accent-text)]">
              {eyebrow}
            </p>
          )}
          <h2 className="mt-4 text-balance text-[28px] font-medium tracking-[-0.02em] text-[var(--ui-text)] sm:text-[36px]">
            {title}
          </h2>
          {note === undefined ? null : (
            <p className="mt-4 text-pretty text-[15px] leading-7 text-[var(--ui-text-muted)] sm:text-[16px]">{note}</p>
          )}
          {action === undefined ? null : (
            <Link
              className="group mt-6 inline-flex items-center gap-1.5 rounded-[var(--ui-radius-control)] text-[15px] font-medium text-[var(--ui-text)] outline-none transition-colors duration-[var(--ui-transition-fast)] hover:text-[var(--ui-accent-text)] focus-visible:ring-2 focus-visible:ring-[var(--ui-focus)]"
              {...resolvedRouteHref(action.to)}
            >
              {action.label}
              <ArrowRight className="size-3.5 transition-transform duration-[var(--ui-transition-standard)] ease-[var(--ui-ease-standard)] group-hover:translate-x-0.5" />
            </Link>
          )}
        </header>
      )}
      <div className={cn(title === undefined ? undefined : 'mt-10 sm:mt-14')}>{children}</div>
    </motion.section>
  );
}
