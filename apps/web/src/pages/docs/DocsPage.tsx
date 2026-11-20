import { getRouteApi, Link, Navigate } from '@tanstack/react-router';
import { ArrowLeft, BookOpen, Sparkles } from 'lucide-react';
import { useAuth } from '@/entities/session';
import { publicAssetPaths } from '@/shared/assets/public-assets';
import { useI18n } from '@/shared/i18n';
import { routes } from '@/shared/routing/paths';
import { Seo } from '@/shared/seo/Seo';
import { Button } from '@/shared/ui/Button';
import { PublicFooter } from '@/widgets/public-footer';
import { defaultDocsSlug, docsContent, docsSlugs, isDocsSlug, personalDocsSlug } from './content';
import './docs.css';

const ownerAvatarSrc = publicAssetPaths.owner;
const docsRoute = getRouteApi('/docs/$slug');
const siteDocsSlugs = docsSlugs.filter((slug) => slug !== personalDocsSlug);

function OwnerAvatar({ size = 'sm' }: { size?: 'sm' | 'md' }) {
  return (
    <span
      aria-hidden="true"
      className={size === 'md' ? 'docs-owner-avatar size-10' : 'docs-owner-avatar size-7'}
      data-slot="docs-owner-avatar"
    >
      <img
        alt=""
        className="size-full object-cover"
        decoding="async"
        referrerPolicy="no-referrer"
        src={ownerAvatarSrc}
      />
    </span>
  );
}

export function DocsPage() {
  const { locale, t } = useI18n();
  const auth = useAuth();
  const { slug } = docsRoute.useParams();
  if (!isDocsSlug(slug)) {
    return <Navigate replace params={{ slug: defaultDocsSlug }} to="/docs/$slug" />;
  }

  const pages = docsContent[locale];
  const page = pages[slug];
  const ownerTitle = pages[personalDocsSlug].title;
  const isPersonalPage = slug === personalDocsSlug;
  const stickyTopClass = auth.role === 'guest' ? 'top-24' : 'top-8';

  return (
    <>
      <Seo title={page.title} description={page.description} path={routes.docs(slug)} />
      <div className="docs-layout" data-slot="docs-layout">
        <aside className="docs-sidebar hidden lg:block" data-slot="docs-sidebar">
          <div className={`docs-sidebar-sticky sticky ${stickyTopClass}`}>
            <Button asChild className="w-fit" size="sm" variant="secondary">
              <Link to={routes.home}>
                <ArrowLeft className="size-4" />
                {t('docs.home')}
              </Link>
            </Button>

            <Link
              className={isPersonalPage ? 'docs-personal-link is-active' : 'docs-personal-link'}
              data-slot="docs-personal-link"
              params={{ slug: personalDocsSlug }}
              to="/docs/$slug"
            >
              <div className="flex items-center gap-3">
                <OwnerAvatar size="md" />
                <span className="min-w-0">
                  <span className="docs-nav-label">{t('docs.badge')}</span>
                  <span className="docs-personal-title">{ownerTitle}</span>
                </span>
              </div>
            </Link>

            <div className="docs-navigation" data-slot="docs-navigation">
              <div className="docs-nav-heading">
                <BookOpen className="size-3.5" />
                {t('docs.sectionNav')}
              </div>
              <nav className="grid gap-1">
                {siteDocsSlugs.map((itemSlug) => (
                  <Link
                    className={itemSlug === slug ? 'docs-nav-link is-active' : 'docs-nav-link'}
                    data-slot="docs-nav-link"
                    key={itemSlug}
                    params={{ slug: itemSlug }}
                    to="/docs/$slug"
                  >
                    <span>{pages[itemSlug].title}</span>
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </aside>

        <main className="docs-main" data-slot="docs-main">
          <nav aria-label={t('docs.sectionNav')} className="docs-breadcrumb" data-slot="docs-breadcrumb">
            <Link to={routes.home}>{t('nav.home')}</Link>
            <span aria-hidden="true">/</span>
            <Link params={{ slug: defaultDocsSlug }} to="/docs/$slug">
              {t('nav.docs')}
            </Link>
            <span aria-hidden="true">/</span>
            <span className="text-[var(--ui-text)]">{page.title}</span>
          </nav>

          <article className="docs-article" data-slot="docs-article">
            <header className="docs-article-header">
              <span className={isPersonalPage ? 'docs-context is-personal' : 'docs-context'} data-slot="docs-context">
                {isPersonalPage ? <OwnerAvatar /> : <Sparkles className="size-3.5" />}
                {t('docs.badge')}
              </span>
              <h1>{page.title}</h1>
              <p>{page.description}</p>
            </header>

            <div className="docs-sections" data-slot="docs-sections">
              {page.sections.map((section) => (
                <section
                  className="docs-section scroll-mt-28"
                  data-slot="docs-section"
                  id={section.id}
                  key={section.id}
                >
                  <h2>{section.title}</h2>
                  <div className="docs-section-body">
                    {section.body.map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </article>

          <nav
            aria-label={t('docs.sectionNav')}
            className="docs-mobile-navigation lg:hidden"
            data-slot="docs-mobile-navigation"
          >
            <Link className="docs-mobile-personal-link" params={{ slug: personalDocsSlug }} to="/docs/$slug">
              <span>{ownerTitle}</span>
              <OwnerAvatar />
            </Link>
            {siteDocsSlugs.map((itemSlug) => (
              <Link
                className={itemSlug === slug ? 'docs-mobile-nav-link is-active' : 'docs-mobile-nav-link'}
                key={itemSlug}
                params={{ slug: itemSlug }}
                to="/docs/$slug"
              >
                {pages[itemSlug].title}
              </Link>
            ))}
          </nav>
        </main>

        <aside className="docs-outline hidden xl:block" data-slot="docs-outline">
          <div className={`docs-outline-sticky sticky ${stickyTopClass}`}>
            <span className="docs-outline-heading">{t('docs.onThisPage')}</span>
            <nav className="grid gap-2">
              {page.sections.map((section) => (
                <a className="docs-outline-link" href={`#${section.id}`} key={section.id}>
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

export function DocsIndexPage() {
  return <Navigate replace params={{ slug: defaultDocsSlug }} to="/docs/$slug" />;
}
