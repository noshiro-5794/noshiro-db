import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import '@/shared/ui/motion.css';

/**
 * The first thing a visitor reads.
 *
 * A centred display headline over a faint accent glow, with the two things a
 * newcomer can do next: search the catalogue, or see what airs this week.
 */
export function LandingHero() {
  const { t } = useI18n();

  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-[-280px] h-[560px] bg-[radial-gradient(50%_50%_at_50%_50%,var(--ui-accent-soft),transparent_70%)]"
      />
      <div className="relative mx-auto max-w-[1160px] px-4 pb-14 pt-16 text-center sm:pt-24">
        <p className="motion-rise inline-flex items-center gap-2 rounded-[var(--ui-radius-pill)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] px-3 py-1 text-[12px] font-medium text-[var(--ui-text-muted)]">
          <span aria-hidden className="size-1.5 rounded-full bg-[var(--ui-accent)]" />
          {t('public.heroChip')}
        </p>
        <h1 className="motion-rise motion-delay-1 mx-auto mt-6 max-w-[720px] text-balance text-[32px] font-semibold leading-[1.16] tracking-[-0.02em] text-[var(--ui-text)] sm:text-[46px]">
          {t('public.heroTitle')}
        </h1>
        <p className="motion-rise motion-delay-2 mx-auto mt-5 max-w-[600px] text-[15px] leading-7 text-[var(--ui-text-muted)]">
          {t('public.heroBody')}
        </p>
        <div className="motion-rise motion-delay-3 mt-8 flex flex-wrap items-center justify-center gap-3">
          <Button asChild size="lg">
            <Link to={routes.search}>{t('public.startSearch')}</Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link to={routes.airing}>{t('public.viewSchedule')}</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
