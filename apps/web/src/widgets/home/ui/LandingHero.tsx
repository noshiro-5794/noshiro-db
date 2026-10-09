import { Link } from '@tanstack/react-router';
import { motion } from 'motion/react';
import { useI18n } from '@/shared/i18n';
import { enterVariants, heroStackVariants } from '@/shared/lib/motion';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';

/**
 * The first thing a visitor reads.
 *
 * dub's hero composition: a centred stack on the page background — pill,
 * display heading, one paragraph, two actions — with the page's own surfaces
 * rather than a decorated panel. The stack rises in sequence on mount.
 */
export function LandingHero() {
  const { t } = useI18n();

  return (
    <section className="mx-auto w-full max-w-[1160px] px-4 pb-6 pt-20 text-center sm:pb-10 sm:pt-28">
      <motion.div
        animate="visible"
        className="mx-auto flex max-w-[720px] flex-col items-center"
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
    </section>
  );
}
