import type { ComponentProps, ReactNode } from 'react';
import { LoaderCircle, Search, type LucideIcon } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/shared/ui/InputGroup';

// `size` on an input is the native character-width attribute, so the control rung replaces it.
type SearchFieldProps = Omit<ComponentProps<typeof InputGroupInput>, 'size' | 'type'> & {
  'aria-label': string;
  size?: 'default' | 'lg';
};

type ResultsMetaProps = ComponentProps<'div'> & {
  actions?: ReactNode;
  count?: number | undefined;
  label: ReactNode;
  pending?: boolean;
  pendingLabel?: string;
};

type ResultsStatus = 'empty' | 'error' | 'loading' | 'ready';

type ResultsStateProps = {
  children: ReactNode;
  emptyAction?: ReactNode;
  emptyDescription?: string;
  emptyIcon?: LucideIcon;
  /** `inline` for a section that sits inside a page with other content. */
  emptyVariant?: 'card' | 'inline';
  emptyTitle: string;
  errorDescription?: string;
  errorTitle: string;
  loadingTitle: string;
  status: ResultsStatus;
};

function DataToolbar({ className, ...props }: ComponentProps<'form'>) {
  return (
    <form
      className={cn('grid gap-2.5 border-b border-border-subtle pb-3', className)}
      data-slot="data-toolbar"
      {...props}
    />
  );
}

function DataToolbarRow({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('grid items-center gap-2', className)} data-slot="data-toolbar-row" {...props} />;
}

function DataToolbarPrimary({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('min-w-0', className)} data-slot="data-toolbar-primary" {...props} />;
}

function DataToolbarFilters({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        // A phone stacks five full-width selects and pushes the first result a
        // screen down, so the row scrolls sideways there and wraps from sm up.
        'flex flex-nowrap gap-2 overflow-x-auto pb-1 sm:flex-wrap sm:overflow-visible sm:pb-0',
        className,
      )}
      data-slot="data-toolbar-filters"
      {...props}
    />
  );
}

function SearchField({ className, size = 'default', ...props }: SearchFieldProps) {
  return (
    <InputGroup data-slot="search-field" size={size}>
      <InputGroupAddon aria-hidden="true">
        <Search />
      </InputGroupAddon>
      <InputGroupInput className={className} type="search" {...props} />
    </InputGroup>
  );
}

function ResultsMeta({
  actions,
  children,
  className,
  count,
  label,
  pending = false,
  pendingLabel,
  ...props
}: ResultsMetaProps) {
  return (
    <div
      className={cn(
        'flex min-h-6 flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground',
        className,
      )}
      data-slot="results-meta"
      {...props}
    >
      <div className="flex min-w-0 flex-wrap items-center gap-2" data-slot="results-meta-count">
        <strong className="font-semibold tabular-nums text-foreground">
          {count === undefined ? (
            <span
              aria-hidden="true"
              className="block h-3 w-5 animate-pulse rounded-[var(--ui-radius-control)] bg-[var(--ui-bg-muted)]"
            />
          ) : (
            count
          )}
        </strong>
        <span>{label}</span>
        {children}
      </div>
      {pending || actions ? (
        <div className="flex flex-wrap items-center justify-end gap-2" data-slot="results-meta-actions">
          {pending && pendingLabel ? (
            <span aria-live="polite" className="inline-flex items-center gap-1.5" role="status">
              <LoaderCircle aria-hidden="true" className="size-3.5 animate-spin" />
              {pendingLabel}
            </span>
          ) : null}
          {actions}
        </div>
      ) : null}
    </div>
  );
}

type ListSurfaceProps = ComponentProps<'div'> & {
  variant?: 'bordered' | 'flat';
};

function ListSurface({ className, variant = 'bordered', ...props }: ListSurfaceProps) {
  return (
    <div
      className={cn(
        'grid min-w-0',
        variant === 'bordered' && 'overflow-hidden rounded-[var(--ui-radius-control)] border border-border bg-surface',
        className,
      )}
      data-slot="list-surface"
      data-variant={variant}
      {...props}
    />
  );
}

function ResultsState({
  children,
  emptyAction,
  emptyDescription,
  emptyIcon,
  emptyVariant = 'card',
  emptyTitle,
  errorDescription,
  errorTitle,
  loadingTitle,
  status,
}: ResultsStateProps) {
  if (status === 'loading') return <LoadingState title={loadingTitle} />;
  if (status === 'error') {
    return (
      <ErrorState title={errorTitle} {...(errorDescription === undefined ? {} : { description: errorDescription })} />
    );
  }
  if (status === 'empty') {
    return (
      <EmptyState
        {...(emptyAction === undefined ? {} : { action: emptyAction })}
        {...(emptyDescription === undefined ? {} : { description: emptyDescription })}
        {...(emptyIcon === undefined ? {} : { icon: emptyIcon })}
        title={emptyTitle}
        variant={emptyVariant}
      />
    );
  }
  return children;
}

export {
  DataToolbar,
  DataToolbarFilters,
  DataToolbarPrimary,
  DataToolbarRow,
  ListSurface,
  ResultsMeta,
  ResultsState,
  SearchField,
};
export type { ResultsStatus };
