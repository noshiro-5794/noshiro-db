import type { ComponentProps, ReactNode } from 'react';
import { cn } from '@/shared/lib/cn';

type DetailHeaderProps = Omit<ComponentProps<'header'>, 'title'> & {
  badges?: ReactNode;
  description?: ReactNode;
  meta?: ReactNode;
  title: ReactNode;
  titleId: string;
};

function DetailHeader({ badges, className, description, meta, title, titleId, ...props }: DetailHeaderProps) {
  return (
    <header
      className={cn('grid gap-4 border-b border-border-subtle pb-5', className)}
      data-slot="detail-header"
      {...props}
    >
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="m-0 text-xl font-semibold leading-tight text-foreground sm:text-2xl" id={titleId}>
            {title}
          </h1>
          {description ? (
            <div className="mt-2 text-sm leading-6 text-muted-foreground" data-slot="detail-description">
              {description}
            </div>
          ) : null}
        </div>
        {badges ? (
          <div className="flex shrink-0 flex-wrap items-center gap-1.5 sm:justify-end" data-slot="detail-badges">
            {badges}
          </div>
        ) : null}
      </div>
      {meta ? (
        <div className="flex min-w-0 flex-wrap items-center gap-3" data-slot="detail-meta">
          {meta}
        </div>
      ) : null}
    </header>
  );
}

function DetailBody({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('min-w-0 [overflow-wrap:anywhere]', className)} data-slot="detail-body" {...props} />;
}

function DetailFooter({ className, ...props }: ComponentProps<'footer'>) {
  return (
    <footer
      className={cn(
        'flex min-w-0 flex-wrap items-center justify-end gap-2 border-t border-border-subtle pt-4',
        className,
      )}
      data-slot="detail-footer"
      {...props}
    />
  );
}

type DetailSectionProps = Omit<ComponentProps<'section'>, 'title'> & {
  actions?: ReactNode;
  meta?: ReactNode;
  title: ReactNode;
  titleId: string;
};

function DetailSection({ actions, children, className, meta, title, titleId, ...props }: DetailSectionProps) {
  return (
    <section
      className={cn('grid min-w-0 gap-4 border-t border-border-subtle pt-5', className)}
      aria-labelledby={titleId}
      {...props}
    >
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3" data-slot="detail-section-header">
        <div className="min-w-0">
          <h2 className="m-0 text-base font-semibold leading-6 text-foreground" id={titleId}>
            {title}
          </h2>
          {meta ? <div className="mt-0.5 text-xs text-muted-foreground">{meta}</div> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

export { DetailBody, DetailFooter, DetailHeader, DetailSection };
