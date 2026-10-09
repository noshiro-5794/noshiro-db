import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';

/**
 * The closing invitation, for visitors who scrolled the whole page. The source
 * line sits here rather than in the hero: it answers a question people ask
 * after they have already seen what the catalogue contains.
 */
export function LandingClosingCta() {
  const { t } = useI18n();

  return (
    <section className="mx-auto w-full max-w-[1160px] px-4 pb-16 pt-16 sm:pb-24 sm:pt-24">
      <div className="relative overflow-hidden rounded-[var(--ui-radius-frame)] border border-[var(--ui-border)] bg-[var(--ui-bg-surface)] px-6 py-12 text-center sm:py-16">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 bottom-[-160px] h-[320px] bg-[radial-gradient(50%_50%_at_50%_50%,var(--ui-accent-soft),transparent_70%)]"
        />
        <h2 className="relative text-balance text-[24px] font-semibold tracking-[-0.01em] text-[var(--ui-text)] sm:text-[28px]">
          {t('public.ctaTitle')}
        </h2>
        <p className="relative mx-auto mt-3 max-w-[520px] text-[14px] leading-6 text-[var(--ui-text-muted)]">
          {t('public.ctaBody')}
        </p>
        <div className="relative mt-7 flex flex-wrap items-center justify-center gap-3">
          <Button asChild size="lg">
            <Link to={routes.register}>{t('auth.register')}</Link>
          </Button>
          <Button asChild size="lg" variant="ghost">
            <Link to={routes.login}>{t('auth.login')}</Link>
          </Button>
        </div>
        <p className="relative mt-8 text-[12px] text-[var(--ui-text-subtle)]">{t('public.ctaSources')}</p>
      </div>
    </section>
  );
}
