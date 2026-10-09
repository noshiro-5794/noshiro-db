import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { LandingSection } from './LandingSection';
import './landing.css';

/**
 * The closing invitation.
 *
 * The hero's panel treatment again — grid, glow, centred stack — so the page
 * ends where it began. The source line sits here rather than up top: it answers
 * a question people ask after they have seen what the catalogue holds.
 */
export function LandingClosingCta() {
  const { t } = useI18n();

  return (
    <LandingSection className="pb-20 pt-20 sm:pb-28 sm:pt-28">
      <div className="landing-panel relative isolate mx-auto max-w-[1000px] overflow-hidden rounded-[20px] border border-[var(--ui-border-subtle)] px-6 py-14 text-center sm:px-12 sm:py-20">
        <div aria-hidden="true" className="landing-grid pointer-events-none absolute inset-0" />
        <div
          aria-hidden="true"
          className="landing-glow pointer-events-none absolute -top-40 left-1/2 h-[320px] w-[130%] -translate-x-1/2 opacity-60 blur-[90px]"
        />

        <div className="relative mx-auto max-w-2xl">
          <h2 className="text-balance text-[26px] font-medium tracking-[-0.015em] text-[var(--ui-text)] sm:text-[34px]">
            {t('public.ctaTitle')}
          </h2>
          <p className="mt-4 text-pretty text-[15px] leading-7 text-[var(--ui-text-muted)]">{t('public.ctaBody')}</p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button asChild size="lg">
              <Link to={routes.register}>{t('auth.register')}</Link>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <Link to={routes.login}>{t('auth.login')}</Link>
            </Button>
          </div>
          <p className="mt-9 text-[12px] text-[var(--ui-text-subtle)]">{t('public.ctaSources')}</p>
        </div>
      </div>
    </LandingSection>
  );
}
