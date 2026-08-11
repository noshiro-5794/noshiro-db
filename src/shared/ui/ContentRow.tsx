import type { ComponentProps } from 'react';
import { cn } from '@/shared/lib/cn';

function ContentRow({ className, ...props }: ComponentProps<'article'>) {
  return (
    <article
      className={cn(
        'group/content-row grid min-w-0 gap-3 border-b border-border-subtle px-3 py-3 transition-colors last:border-b-0 hover:bg-muted sm:grid-cols-[64px_minmax(0,1fr)] sm:gap-4 sm:px-4 sm:py-4',
        className,
      )}
      data-slot="content-row"
      {...props}
    />
  );
}

function ContentRowMedia({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'hidden h-[88px] w-16 overflow-hidden rounded-sm border border-border bg-muted sm:block [&>a]:grid [&>a]:size-full [&_img]:size-full [&_img]:object-cover [&_span]:grid [&_span]:size-full [&_span]:place-items-center [&_span]:bg-[var(--ui-accent-soft)] [&_span]:text-[var(--ui-accent-text)]',
        className,
      )}
      data-slot="content-row-media"
      {...props}
    />
  );
}

function ContentRowMain({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('grid min-w-0 content-center gap-2', className)} data-slot="content-row-main" {...props} />;
}

function ContentRowMeta({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-muted-foreground', className)}
      data-slot="content-row-meta"
      {...props}
    />
  );
}

function ContentRowHeading({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('flex min-w-0 items-start justify-between gap-3', className)}
      data-slot="content-row-heading"
      {...props}
    />
  );
}

type ContentRowTitleProps = ComponentProps<'h2'> & {
  as?: 'h2' | 'h3';
};

function ContentRowTitle({ as: Heading = 'h2', className, ...props }: ContentRowTitleProps) {
  return (
    <Heading
      className={cn(
        'm-0 line-clamp-2 min-w-0 flex-1 text-[15px] font-semibold leading-5 text-foreground [&_a]:transition-colors [&_a:hover]:text-[var(--ui-accent-text)]',
        className,
      )}
      data-slot="content-row-title"
      {...props}
    />
  );
}

function ContentRowExcerpt({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('[&>p]:line-clamp-3 [&>p]:text-sm [&>p]:leading-6 [&>p]:text-muted-foreground', className)}
      data-slot="content-row-excerpt"
      {...props}
    />
  );
}

function ContentRowReference({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'mt-0.5 min-w-0 [&>a]:flex [&>a]:w-fit [&>a]:max-w-full [&>a]:min-w-0 [&>a]:items-center [&>a]:gap-2 [&>a]:rounded-full [&>a]:border [&>a]:border-border [&>a]:bg-muted [&>a]:px-2.5 [&>a]:py-1 [&>a]:text-xs [&>a]:font-medium [&>a]:text-muted-foreground [&>a]:transition-colors [&>a:hover]:border-[var(--ui-accent-border)] [&>a:hover]:text-[var(--ui-accent-text)] [&_small]:shrink-0 [&_small]:text-subtle-foreground [&_span]:truncate',
        className,
      )}
      data-slot="content-row-reference"
      {...props}
    />
  );
}

function ContentRowFooter({ className, ...props }: ComponentProps<'footer'>) {
  return (
    <footer
      className={cn('mt-0.5 flex min-w-0 flex-wrap items-center justify-between gap-3', className)}
      data-slot="content-row-footer"
      {...props}
    />
  );
}

function ContentRowAuthor({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'min-w-0 [&>a]:inline-flex [&>a]:min-w-0 [&>a]:items-center [&>a]:gap-2 [&>a]:text-xs [&>a]:font-medium [&>a]:text-muted-foreground [&>a]:transition-colors [&>a:hover]:text-[var(--ui-accent-text)] [&_img]:size-6 [&_img]:shrink-0 [&_img]:rounded-full [&_img]:bg-muted [&_img]:object-cover [&_span]:truncate',
        className,
      )}
      data-slot="content-row-author"
      {...props}
    />
  );
}

function ContentRowActions({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('flex shrink-0 flex-wrap items-center gap-1', className)}
      data-slot="content-row-actions"
      {...props}
    />
  );
}

export {
  ContentRow,
  ContentRowActions,
  ContentRowAuthor,
  ContentRowExcerpt,
  ContentRowFooter,
  ContentRowHeading,
  ContentRowMain,
  ContentRowMedia,
  ContentRowMeta,
  ContentRowReference,
  ContentRowTitle,
};
