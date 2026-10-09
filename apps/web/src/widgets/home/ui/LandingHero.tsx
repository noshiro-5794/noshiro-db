import { Link } from '@tanstack/react-router';
import { ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';
import { useI18n } from '@/shared/i18n';
import { enterVariants, heroStackVariants } from '@/shared/lib/motion';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';

/** A quiet, centred introduction to the public catalogue. */
export function LandingHero() {
  const { t } = useI18n();

  return (
    <section className="landing-hero">
      <motion.div animate="visible" className="landing-hero-stack" initial="hidden" variants={heroStackVariants}>
        <motion.p className="landing-hero-eyebrow" variants={enterVariants}>
          {t('public.heroChip')}
        </motion.p>

        <motion.h1 className="landing-hero-title" variants={enterVariants}>
          {t('public.heroTitle')}
        </motion.h1>

        <motion.p className="landing-hero-description" variants={enterVariants}>
          {t('public.heroBody')}
        </motion.p>

        <motion.div className="landing-hero-actions" variants={enterVariants}>
          <Button asChild className="public-button public-button-primary" variant="unstyled">
            <Link to={routes.search}>{t('public.startSearch')}</Link>
          </Button>
          <Button asChild className="public-button public-button-secondary" variant="unstyled">
            <Link to={routes.airing}>
              {t('public.viewSchedule')}
              <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
          </Button>
        </motion.div>
      </motion.div>
    </section>
  );
}
