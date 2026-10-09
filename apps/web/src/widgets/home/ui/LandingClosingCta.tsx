import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Button } from '@/shared/ui/Button';
import { LandingSection } from './LandingSection';

/**
 * The closing invitation.
 *
 * A centred stack behind a hairline, so the page ends the way it began without
 * a second decorated surface. The source line sits here rather than up top: it
 * answers a question people ask after they have seen what the catalogue holds.
 */
export function LandingClosingCta() {
  const { t } = useI18n();

  return (
    <LandingSection className="pt-20 sm:pt-28">
      <div className="mt-4 border-t border-[var(--ui-border-subtle)] pt-16 text-center sm:pt-20">
        <div className="mx-auto max-w-2xl">
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
