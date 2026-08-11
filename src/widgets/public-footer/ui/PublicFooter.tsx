import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';

type PublicFooterProps = {
  variant?: 'public' | 'compact';
};

type FooterLink = { type: 'route'; label: string; to: string } | { type: 'external'; label: string; href: string };

const githubProfileUrl = 'https://github.com/noshiro-5794/';
const contactEmail = 'hello@noshiro.moe';

export function PublicFooter({ variant = 'public' }: PublicFooterProps) {
  const { t } = useI18n();
  const isCompact = variant === 'compact';
  const footerLinks: FooterLink[] = [
    { type: 'route', label: t('footer.terms'), to: routes.docs('terms') },
    { type: 'route', label: t('footer.privacy'), to: routes.docs('privacy') },
    { type: 'route', label: t('footer.security'), to: routes.docs('security') },
    { type: 'route', label: t('footer.status'), to: routes.docs('status') },
    { type: 'route', label: t('footer.community'), to: routes.docs('community') },
    { type: 'route', label: t('nav.docs'), to: routes.docsIntroduction },
    { type: 'external', label: t('footer.contact'), href: `mailto:${contactEmail}` },
    { type: 'external', label: 'GitHub', href: githubProfileUrl },
  ];

  return (
    <footer
      className={
        isCompact
          ? 'border-t border-[color-mix(in_srgb,var(--ui-border)_58%,transparent)]'
          : 'border-t border-[color-mix(in_srgb,var(--ui-border)_58%,transparent)] bg-[var(--ui-bg-canvas)]'
      }
    >
      <div
        className={`mx-auto flex max-w-6xl flex-col-reverse gap-4 px-5 text-xs text-[var(--ui-text-muted)] ${isCompact ? 'py-5' : 'py-7'} lg:flex-row lg:items-center lg:justify-between`}
      >
        <div className="flex min-w-0 items-center gap-2">
          <Link
            className="inline-flex shrink-0 text-[var(--ui-text-muted)] transition hover:text-[var(--ui-text)]"
            to={routes.home}
            aria-label="Noshiro DB"
          >
            <img className="size-5 rounded-md opacity-80" src="/brand/icon.svg" alt="" aria-hidden="true" />
          </Link>
          <span>© 2026 Noshiro DB</span>
        </div>

        <nav className="flex flex-wrap gap-x-4 gap-y-2" aria-label={t('footer.navigation')}>
          {footerLinks.map((item) => {
            if (item.type === 'route') {
              return (
                <Link className="transition hover:text-[var(--ui-text)]" key={item.label} to={item.to}>
                  {item.label}
                </Link>
              );
            }

            return (
              <a
                className="transition hover:text-[var(--ui-text)]"
                href={item.href}
                key={item.label}
                rel="noreferrer"
                target={item.href.startsWith('mailto:') ? undefined : '_blank'}
              >
                {item.label}
              </a>
            );
          })}
        </nav>
      </div>
    </footer>
  );
}
