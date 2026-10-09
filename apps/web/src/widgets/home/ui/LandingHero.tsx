import { Link } from '@tanstack/react-router';
import { motion } from 'motion/react';
import { useI18n } from '@/shared/i18n';
import { enterVariants, heroStackVariants } from '@/shared/lib/motion';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import './landing.css';

/**
 * The first thing a visitor reads.
 *
 * dub's hero composition: one rounded panel holding a masked hairline grid and
 * a soft accent glow, with the copy centred inside it. The stack rises in
 * sequence on mount rather than all at once.
 */
export function LandingHero() {
  const { t } = useI18n();

  return (
    <section className="mx-auto w-full max-w-[1160px] px-4 pt-6 sm:pt-10">
      <div className="landing-panel relative isolate overflow-hidden rounded-[20px] border border-[var(--ui-border-subtle)] px-6 py-14 text-center sm:px-12 sm:py-20">
        <div aria-hidden="true" className="landing-grid pointer-events-none absolute inset-0" />
        <div
          aria-hidden="true"
          className="landing-glow pointer-events-none absolute -bottom-32 left-1/2 h-[360px] w-[130%] -translate-x-1/2 opacity-70 blur-[90px]"
        />

        <motion.div
          animate="visible"
          className="relative mx-auto flex max-w-[720px] flex-col items-center"
          initial="hidden"
          variants={heroStackVariants}
        >
          <motion.p
            className="inline-flex items-center gap-2 rounded-[var(--ui-radius-pill)] border border-[var(--ui-border)] bg-[var(--ui-bg-elevated)] px-3 py-1 text-[12px] font-medium text-[var(--ui-text-muted)]"
            variants={enterVariants}
          >
            <span aria-hidden className="size-1.5 rounded-full bg-[var(--ui-accent)]" />
            {t('public.heroChip')}
          </motion.p>

          <motion.h1
            className="mt-7 text-balance text-[34px] font-semibold leading-[1.1] tracking-[-0.025em] text-[var(--ui-text)] sm:text-[54px]"
            variants={enterVariants}
          >
            {t('public.heroTitle')}
          </motion.h1>

          <motion.p
            className="mt-6 max-w-[604px] text-pretty text-[15px] leading-7 text-[var(--ui-text-muted)]"
            variants={enterVariants}
          >
            {t('public.heroBody')}
          </motion.p>

          <motion.div className="mt-9 flex flex-wrap items-center justify-center gap-3" variants={enterVariants}>
            <Button asChild size="lg">
              <Link to={routes.search}>{t('public.startSearch')}</Link>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <Link to={routes.airing}>{t('public.viewSchedule')}</Link>
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
