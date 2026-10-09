import { Link } from '@tanstack/react-router';
import { motion } from 'motion/react';
import { useI18n } from '@/shared/i18n';
import { enterVariants, heroStackVariants } from '@/shared/lib/motion';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';

/**
 * The first thing a visitor reads.
 *
 * plane's marketing hero: a letterspaced eyebrow, a display heading set in one
 * measure and one weight, a single wide paragraph, then the two actions. The
 * stack rises in sequence on mount.
 */
export function LandingHero() {
  const { t } = useI18n();

  return (
    <section className="mx-auto w-full max-w-[1160px] px-4 pb-10 pt-16 text-center sm:pb-14 sm:pt-24">
      <motion.div
        animate="visible"
        className="mx-auto flex max-w-[980px] flex-col items-center"
        initial="hidden"
        variants={heroStackVariants}
      >
        <motion.p
          className="text-[13px] font-semibold uppercase tracking-[0.08em] text-[var(--ui-accent-text)]"
          variants={enterVariants}
        >
          {t('public.heroChip')}
        </motion.p>

        <motion.h1
          className="mt-6 text-balance text-[38px] font-medium leading-[1.06] tracking-[-0.03em] text-[var(--ui-text)] sm:text-[56px] lg:text-[64px]"
          variants={enterVariants}
        >
          {t('public.heroTitle')}
        </motion.h1>

        <motion.p
          className="mt-7 max-w-[620px] text-pretty text-[17px] leading-8 text-[var(--ui-text-muted)] sm:text-[20px]"
          variants={enterVariants}
        >
          {t('public.heroBody')}
        </motion.p>

        <motion.div className="mt-10 flex flex-wrap items-center justify-center gap-3" variants={enterVariants}>
          <Button asChild size="xl">
            <Link to={routes.search}>{t('public.startSearch')}</Link>
          </Button>
          <Button asChild size="xl" variant="secondary">
            <Link to={routes.airing}>{t('public.viewSchedule')}</Link>
          </Button>
        </motion.div>
      </motion.div>
    </section>
  );
}
