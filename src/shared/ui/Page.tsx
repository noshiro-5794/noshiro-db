import type { ReactNode } from 'react';
import { Seo } from '@/shared/seo/Seo';
import { cn } from '@/shared/lib/cn';

type PageWidth = 'default' | 'full' | 'reader' | 'wide';
type PagePadding = 'default' | 'none';
type PageHeaderMode = 'context' | 'title';

type PageProps = {
  title: string;
  actions?: ReactNode;
  children?: ReactNode;
  description?: string | undefined;
  eyebrow?: string;
  headerMode?: PageHeaderMode;
  hideHeader?: boolean;
  leading?: ReactNode;
  padding?: PagePadding;
  seo?: boolean;
  seoDescription?: string | undefined;
  width?: PageWidth;
};

const widthClasses: Record<PageWidth, string> = {
  default: 'max-w-[var(--ui-content-width)]',
  wide: 'max-w-[1600px]',
  reader: 'max-w-[960px]',
  full: 'max-w-none',
};

function PageTopbar({
  actions,
  description,
  eyebrow,
  headerMode,
  leading,
  title,
  width,
}: {
  actions: ReactNode | undefined;
  description: string | undefined;
  eyebrow: string | undefined;
  headerMode: PageHeaderMode;
  leading: ReactNode | undefined;
  title: string;
  width: PageWidth;
}) {
  return (
    <header
      className="sticky top-[var(--ui-sticky-page-top)] z-[var(--ui-layer-page-topbar)] h-[var(--ui-page-topbar-height)] shrink-0 overflow-hidden border-b border-border-subtle bg-[color-mix(in_srgb,var(--ui-bg-surface)_92%,transparent)] backdrop-blur-xl"
      data-mode={headerMode}
      data-slot="page-topbar"
    >
      <div className={cn('mx-auto flex h-full w-full items-center gap-3 px-4 sm:px-5', widthClasses[width])}>
        {leading ? (
          <div className="flex shrink-0 items-center" data-slot="page-leading">
            {leading}
          </div>
        ) : null}
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <div className="flex min-w-0 items-center gap-1.5 text-xs">
            {eyebrow ? (
              <>
                <span className="shrink-0 text-subtle-foreground">{eyebrow}</span>
                <span aria-hidden="true" className="text-[var(--ui-border-strong)]">
                  /
                </span>
              </>
            ) : null}
            {headerMode === 'title' ? (
              <h1 className="m-0 min-w-0 truncate text-sm font-semibold leading-5 text-foreground" title={title}>
                {title}
              </h1>
            ) : (
              <span
                className="min-w-0 truncate text-sm font-semibold leading-5 text-foreground"
                data-slot="page-context-title"
                title={title}
              >
                {title}
              </span>
            )}
          </div>
          {description ? (
            <p
              className="m-0 hidden min-w-0 truncate text-xs leading-5 text-muted-foreground sm:block"
              title={description}
            >
              {description}
            </p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex max-w-[70%] shrink-0 items-center gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {actions}
          </div>
        ) : null}
      </div>
    </header>
  );
}

export function Page({
  title,
  actions,
  children,
  description,
  eyebrow,
  headerMode = 'title',
  hideHeader = false,
  leading,
  padding = 'default',
  seo = true,
  seoDescription,
  width = 'default',
}: PageProps) {
  const resolvedSeoDescription = seoDescription ?? description;

  return (
    <section className="flex min-h-full flex-col" data-slot="page">
      {seo ? (
        <Seo title={title} {...(resolvedSeoDescription === undefined ? {} : { description: resolvedSeoDescription })} />
      ) : null}
      {hideHeader && headerMode === 'title' ? <h1 className="sr-only">{title}</h1> : null}
      {hideHeader ? null : <PageTopbar {...{ actions, description, eyebrow, headerMode, leading, title, width }} />}
      <div
        className={cn(
          'mx-auto w-full flex-1',
          widthClasses[width],
          padding === 'default' && 'px-4 py-4 sm:px-5 lg:py-5',
        )}
        data-slot="page-content"
      >
        {children}
      </div>
    </section>
  );
}
