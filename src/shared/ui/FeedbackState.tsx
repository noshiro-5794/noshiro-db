import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, LoaderCircle, type LucideIcon } from 'lucide-react';
import { cn } from '@/shared/lib/cn';

type FeedbackStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

type FeedbackStateViewProps = FeedbackStateProps & {
  icon: LucideIcon;
  loading?: boolean;
  tone?: 'neutral' | 'danger';
};

function FeedbackStateView({
  action,
  description,
  icon: Icon,
  loading = false,
  title,
  tone = 'neutral',
}: FeedbackStateViewProps) {
  return (
    <div
      className={cn(
        'grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-start gap-3 rounded-[var(--ui-radius-surface)] border border-[var(--ui-border-subtle)] bg-[color-mix(in_srgb,var(--ui-bg-surface)_72%,transparent)] px-3.5 py-3 text-[var(--ui-text-muted)]',
        loading && 'items-center',
      )}
      role={tone === 'danger' ? 'alert' : loading ? 'status' : undefined}
    >
      <span
        aria-hidden="true"
        className={cn(
          'grid size-7 place-items-center rounded-[var(--ui-radius-control)] bg-[var(--ui-bg-muted)] text-[var(--ui-text-muted)]',
          tone === 'danger' && 'text-[var(--ui-danger-text)]',
        )}
      >
        <Icon className={cn('size-3.5', loading && 'animate-spin')} />
      </span>
      <div className="min-w-0">
        <strong className="block text-sm font-medium leading-5 text-[var(--ui-text)]">{title}</strong>
        {description ? <span className="mt-0.5 block text-sm leading-5">{description}</span> : null}
        {action ? <div className="mt-2.5">{action}</div> : null}
      </div>
    </div>
  );
}

export function EmptyState(props: FeedbackStateProps) {
  return <FeedbackStateView icon={Inbox} {...props} />;
}

export function LoadingState(props: FeedbackStateProps) {
  return <FeedbackStateView icon={LoaderCircle} loading {...props} />;
}

export function ErrorState(props: FeedbackStateProps) {
  return <FeedbackStateView icon={AlertTriangle} tone="danger" {...props} />;
}
