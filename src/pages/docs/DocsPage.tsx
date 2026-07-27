import { Link, Navigate, useParams } from '@/shared/routing/navigation';
import { ArrowLeft, BookOpen, Sparkles } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { defaultDocsSlug, docsContent, personalDocsSlug } from './content/docs';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Seo } from '@/shared/seo/Seo';
import { Button } from '@/shared/ui/Button';
import { PublicFooter } from '@/widgets/public-footer';

const ownerAvatarSrc = '/assets/placeholders/avatar.png';

function OwnerAvatar({ size = 'sm' }: { size?: 'sm' | 'md' }) {
  const frameSize = size === 'md' ? 'size-12 rounded-2xl' : 'size-8 rounded-xl';

  return (
    <span
      aria-hidden="true"
      className={`relative inline-flex ${frameSize} shrink-0 overflow-hidden border border-[#7F6FB0]/45 bg-[color-mix(in_srgb,#7F6FB0_10%,var(--color-surface))] shadow-sm ring-2 ring-[color-mix(in_srgb,#7F6FB0_10%,transparent)]`}
    >
      <img className="size-full object-cover" src={ownerAvatarSrc} alt="" />
    </span>
  );
}

export function DocsPage() {
  const { locale, t } = useI18n();
  const auth = useAuth();
  const { slug = defaultDocsSlug } = useParams();
  const content = docsContent[locale];
  const page = content.pages[slug];
  const isPersonalPage = page?.slug === personalDocsSlug;
  const personalNavItem = content.nav.find((item) => item.slug === personalDocsSlug);
  const siteNavItems = content.nav.filter((item) => item.slug !== personalDocsSlug);
  const stickyTopClass = auth.role === 'guest' ? 'top-24' : 'top-8';

  if (!page) {
    return <Navigate replace to={routes.docs(defaultDocsSlug)} />;
  }

  return (
    <>
      <Seo title={page.title} description={page.description} path={routes.docs(page.slug)} />
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-[1320px] gap-8 px-5 py-10 lg:grid-cols-[230px_minmax(0,1fr)_210px] lg:px-8">
        <aside className="hidden lg:block">
          <div className={`sticky ${stickyTopClass} grid gap-5`}>
            <Button asChild className="w-fit" size="sm" variant="secondary">
              <Link to={routes.home}>
                <ArrowLeft className="size-4" />
                {t('docs.home')}
              </Link>
            </Button>

            {personalNavItem ? (
              <Link
                className={
                  isPersonalPage
                    ? 'group grid gap-3 rounded-3xl border border-[#7F6FB0]/45 bg-[color-mix(in_srgb,#7F6FB0_10%,var(--color-surface))] p-3 text-[var(--color-text)] shadow-sm'
                    : 'group grid gap-3 rounded-3xl border border-[color-mix(in_srgb,#7F6FB0_28%,var(--color-border))] bg-[color-mix(in_srgb,var(--color-surface)_70%,transparent)] p-3 text-[var(--color-text)] shadow-sm transition hover:-translate-y-0.5 hover:border-[#7F6FB0]/45 hover:bg-[color-mix(in_srgb,#7F6FB0_8%,var(--color-surface))]'
                }
                to={routes.docs(personalNavItem.slug)}
              >
                <div className="flex items-center justify-between gap-3">
                  <OwnerAvatar size="md" />
                  <span className="h-px min-w-8 flex-1 bg-[linear-gradient(90deg,color-mix(in_srgb,#7F6FB0_58%,transparent),transparent)]" />
                </div>
                <span className="text-sm font-semibold leading-5">{personalNavItem.title}</span>
              </Link>
            ) : null}

            <div className="rounded-3xl border border-[color-mix(in_srgb,var(--color-border)_62%,transparent)] bg-[color-mix(in_srgb,var(--color-surface)_66%,transparent)] p-2 shadow-sm">
              <div className="flex items-center gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-normal text-[var(--color-text-muted)]">
                <BookOpen className="size-3.5" />
                {t('docs.sectionNav')}
              </div>
              <nav className="grid gap-1">
                {siteNavItems.map((item) => {
                  const isActive = item.slug === page.slug;

                  return (
                    <Link
                      className={
                        isActive
                          ? 'rounded-2xl bg-[var(--color-surface-elevated)] px-3 py-2 text-sm font-semibold text-[var(--color-text)] shadow-sm ring-1 ring-[color-mix(in_srgb,var(--color-border)_70%,transparent)]'
                          : 'rounded-2xl px-3 py-2 text-sm text-[var(--color-text-muted)] transition hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]'
                      }
                      key={item.slug}
                      to={routes.docs(item.slug)}
                    >
                      <span>{item.title}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>
          </div>
        </aside>

        <main className="min-w-0">
          <div className="mb-8 flex flex-wrap items-center gap-2 text-sm text-[var(--color-text-muted)]">
            <Link className="transition hover:text-[var(--color-text)]" to={routes.home}>
              {t('nav.home')}
            </Link>
            <span>/</span>
            <Link className="transition hover:text-[var(--color-text)]" to={routes.docs(defaultDocsSlug)}>
              {t('nav.docs')}
            </Link>
            <span>/</span>
            <span className="text-[var(--color-text)]">{page.title}</span>
          </div>

          <article className="max-w-3xl">
            <header className="pb-10">
              <span
                className={
                  isPersonalPage
                    ? 'inline-flex items-center gap-2 rounded-full border border-[#7F6FB0]/40 bg-[color-mix(in_srgb,#7F6FB0_9%,var(--color-surface))] px-3 py-1 text-xs font-semibold text-[#685b91] dark:text-[#c8bcea]'
                    : 'inline-flex items-center gap-2 rounded-full border border-[color-mix(in_srgb,var(--color-border)_75%,transparent)] bg-[var(--color-surface-muted)] px-3 py-1 text-xs font-semibold text-[var(--color-text-muted)]'
                }
              >
                {isPersonalPage ? <OwnerAvatar /> : <Sparkles className="size-3.5" />}
                {t('docs.badge')}
              </span>
              <h1 className="mt-4 text-4xl font-semibold tracking-tight text-[var(--color-text)] sm:text-5xl">
                {page.title}
              </h1>
              <p className="mt-5 max-w-2xl text-lg leading-8 text-[var(--color-text-muted)]">{page.description}</p>
            </header>

            <div className="border-y border-[color-mix(in_srgb,var(--color-border)_64%,transparent)]">
              {page.sections.map((section) => (
                <section
                  className="scroll-mt-28 border-b border-[color-mix(in_srgb,var(--color-border)_64%,transparent)] py-9 last:border-b-0"
                  id={section.id}
                  key={section.id}
                >
                  <h2 className="text-xl font-semibold tracking-tight text-[var(--color-text)] sm:text-2xl">
                    {section.title}
                  </h2>
                  <div className="mt-5 grid gap-4 text-base leading-8 text-[var(--color-text-muted)]">
                    {section.body.map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </article>

          <nav className="mt-10 grid gap-2 border-t border-[var(--color-border)] pt-6 text-sm lg:hidden">
            {personalNavItem ? (
              <Link
                className="inline-flex items-center justify-between rounded-3xl border border-[color-mix(in_srgb,#7F6FB0_34%,var(--color-border))] bg-[color-mix(in_srgb,#7F6FB0_8%,var(--color-surface))] px-3 py-3 font-semibold text-[var(--color-text)] shadow-sm"
                to={routes.docs(personalNavItem.slug)}
              >
                <span>{personalNavItem.title}</span>
                <OwnerAvatar />
              </Link>
            ) : null}
            {siteNavItems.map((item) => (
              <Link
                className={
                  item.slug === page.slug
                    ? 'rounded-2xl bg-[var(--color-surface-muted)] px-3 py-2 font-semibold text-[var(--color-text)]'
                    : 'rounded-2xl px-3 py-2 text-[var(--color-text-muted)] transition hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]'
                }
                key={item.slug}
                to={routes.docs(item.slug)}
              >
                {item.title}
              </Link>
            ))}
          </nav>
        </main>

        <aside className="hidden xl:block">
          <div
            className={`sticky ${stickyTopClass} grid gap-3 rounded-3xl border border-[color-mix(in_srgb,var(--color-border)_62%,transparent)] bg-[color-mix(in_srgb,var(--color-surface)_58%,transparent)] p-4 text-sm shadow-sm`}
          >
            <span className="text-xs font-semibold uppercase tracking-normal text-[var(--color-text-muted)]">
              {t('docs.onThisPage')}
            </span>
            <nav className="grid gap-2">
              {page.sections.map((section) => (
                <a
                  className="text-[var(--color-text-muted)] transition hover:text-[var(--color-text)]"
                  href={`#${section.id}`}
                  key={section.id}
                >
                  {section.title}
                </a>
              ))}
            </nav>
          </div>
        </aside>
      </div>
      {auth.role === 'guest' ? null : <PublicFooter variant="compact" />}
    </>
  );
}
