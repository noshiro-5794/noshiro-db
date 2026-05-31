import { Link, Navigate, useParams } from 'react-router-dom';
import { defaultDocsSlug, docsContent } from '@/features/docs/content/docs';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';

export function DocsPage() {
  const { locale, t } = useI18n();
  const { slug = defaultDocsSlug } = useParams();
  const content = docsContent[locale];
  const page = content.pages[slug];

  if (!page) {
    return <Navigate replace to={routes.docs(defaultDocsSlug)} />;
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-8 px-5 py-10 lg:grid-cols-[220px_minmax(0,1fr)]">
      <aside className="hidden lg:block">
        <div className="sticky top-24 grid gap-6">
          <Link className="text-sm font-semibold text-neutral-950 dark:text-white" to={routes.home}>
            Noshiro DB
          </Link>
          <nav className="grid gap-1 border-l border-neutral-200 pl-4 text-sm dark:border-neutral-800">
            {content.nav.map((item) => {
              const isActive = item.slug === page.slug;

              return (
                <Link
                  className={
                    isActive
                      ? 'font-semibold text-[var(--color-accent-strong)]'
                      : 'text-neutral-500 transition hover:text-neutral-950 dark:text-neutral-400 dark:hover:text-white'
                  }
                  key={item.slug}
                  to={routes.docs(item.slug)}
                >
                  {item.title}
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>

      <main className="min-w-0">
        <div className="mb-8 flex flex-wrap items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
          <Link className="transition hover:text-neutral-950 dark:hover:text-white" to={routes.home}>
            {t('nav.home')}
          </Link>
          <span>/</span>
          <Link className="transition hover:text-neutral-950 dark:hover:text-white" to={routes.docs(defaultDocsSlug)}>
            Docs
          </Link>
          <span>/</span>
          <span className="text-neutral-950 dark:text-white">{page.title}</span>
        </div>

        <article className="max-w-3xl">
          <header className="border-b border-neutral-200 pb-8 dark:border-neutral-800">
            <span className="text-sm font-semibold text-[var(--color-accent-strong)]">Docs</span>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-neutral-950 dark:text-white sm:text-5xl">
              {page.title}
            </h1>
            <p className="mt-4 text-lg leading-8 text-neutral-500 dark:text-neutral-400">{page.description}</p>
          </header>

          <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
            {page.sections.map((section) => (
              <section className="scroll-mt-28 py-8" id={section.id} key={section.id}>
                <h2 className="text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">{section.title}</h2>
                <div className="mt-4 grid gap-4 text-base leading-8 text-neutral-600 dark:text-neutral-300">
                  {section.body.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </article>

        <nav className="mt-10 grid gap-2 border-t border-neutral-200 pt-6 text-sm dark:border-neutral-800 lg:hidden">
          {content.nav.map((item) => (
            <Link
              className={
                item.slug === page.slug
                  ? 'font-semibold text-[var(--color-accent-strong)]'
                  : 'text-neutral-500 transition hover:text-neutral-950 dark:text-neutral-400 dark:hover:text-white'
              }
              key={item.slug}
              to={routes.docs(item.slug)}
            >
              {item.title}
            </Link>
          ))}
        </nav>
      </main>
    </div>
  );
}
