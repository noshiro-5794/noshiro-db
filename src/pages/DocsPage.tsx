import { Link, Navigate, useParams } from 'react-router-dom';
import { ArrowLeft, BookOpen } from 'lucide-react';
import { defaultDocsSlug, docsContent } from '@/features/docs/content/docs';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { Button } from '@/shared/ui/Button';

const docsLabels = {
  'zh-CN': {
    badge: 'Documentation',
    home: '返回首页',
    onThisPage: '本页目录',
    sectionNav: '文档',
  },
  'en-US': {
    badge: 'Documentation',
    home: 'Back home',
    onThisPage: 'On this page',
    sectionNav: 'Docs',
  },
  'ja-JP': {
    badge: 'Documentation',
    home: 'ホームへ戻る',
    onThisPage: 'このページ',
    sectionNav: 'ドキュメント',
  },
} as const;

export function DocsPage() {
  const { locale, t } = useI18n();
  const { slug = defaultDocsSlug } = useParams();
  const content = docsContent[locale];
  const page = content.pages[slug];
  const labels = docsLabels[locale];

  if (!page) {
    return <Navigate replace to={routes.docs(defaultDocsSlug)} />;
  }

  return (
    <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-[1360px] gap-8 px-5 py-8 lg:grid-cols-[240px_minmax(0,1fr)_220px] lg:px-8">
      <aside className="hidden lg:block">
        <div className="sticky top-8 grid gap-5">
          <Button asChild className="w-fit" size="sm" variant="secondary">
            <Link to={routes.home}>
              <ArrowLeft className="size-4" />
              {labels.home}
            </Link>
          </Button>
          <div className="rounded-2xl border border-neutral-200 bg-white/70 p-2 shadow-sm backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/58">
            <div className="flex items-center gap-2 px-3 py-2 text-xs font-black uppercase tracking-[0.18em] text-neutral-400">
              <BookOpen className="size-3.5" />
              {labels.sectionNav}
            </div>
            <nav className="grid gap-1">
              {content.nav.map((item) => {
                const isActive = item.slug === page.slug;

                return (
                  <Link
                    className={
                      isActive
                        ? 'rounded-xl bg-[var(--color-accent-soft)] px-3 py-2 text-sm font-semibold text-[var(--color-accent-strong)]'
                        : 'rounded-xl px-3 py-2 text-sm text-neutral-500 transition hover:bg-neutral-100 hover:text-neutral-950 dark:text-neutral-400 dark:hover:bg-neutral-900 dark:hover:text-white'
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
            <span className="inline-flex items-center rounded-full border border-[var(--color-accent-border)] bg-[var(--color-accent-soft)] px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-[var(--color-accent-strong)]">
              {labels.badge}
            </span>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight text-neutral-950 dark:text-white sm:text-5xl">
              {page.title}
            </h1>
            <p className="mt-5 text-lg leading-8 text-neutral-500 dark:text-neutral-400">{page.description}</p>
          </header>

          <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
            {page.sections.map((section) => (
              <section className="scroll-mt-28 py-9" id={section.id} key={section.id}>
                <h2 className="text-2xl font-semibold tracking-tight text-neutral-950 dark:text-white">{section.title}</h2>
                <div className="mt-5 grid gap-4 text-base leading-8 text-neutral-600 dark:text-neutral-300">
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
                  ? 'rounded-xl bg-[var(--color-accent-soft)] px-3 py-2 font-semibold text-[var(--color-accent-strong)]'
                  : 'rounded-xl px-3 py-2 text-neutral-500 transition hover:bg-neutral-100 hover:text-neutral-950 dark:text-neutral-400 dark:hover:bg-neutral-900 dark:hover:text-white'
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
        <div className="sticky top-8 grid gap-3 rounded-2xl border border-neutral-200 bg-white/70 p-4 text-sm shadow-sm backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/58">
          <span className="text-xs font-black uppercase tracking-[0.18em] text-neutral-400">{labels.onThisPage}</span>
          <nav className="grid gap-2">
            {page.sections.map((section) => (
              <a className="text-neutral-500 transition hover:text-neutral-950 dark:text-neutral-400 dark:hover:text-white" href={`#${section.id}`} key={section.id}>
                {section.title}
              </a>
            ))}
          </nav>
        </div>
      </aside>
    </div>
  );
}
