import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, LoaderCircle } from 'lucide-react';

type FeedbackStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: FeedbackStateProps) {
  return (
    <div className="empty-state">
      <span className="feedback-state-icon" aria-hidden="true">
        <Inbox className="size-4" />
      </span>
      <div className="min-w-0">
        <strong>{title}</strong>
        {description ? <span>{description}</span> : null}
        {action ? <div className="feedback-action">{action}</div> : null}
      </div>
    </div>
  );
}

export function LoadingState({ title, description }: FeedbackStateProps) {
  return (
    <div className="loading-state">
      <span className="feedback-state-icon" aria-hidden="true">
        <LoaderCircle className="size-4 animate-spin" />
      </span>
      <div className="min-w-0">
        <strong>{title}</strong>
        {description ? <span>{description}</span> : null}
      </div>
    </div>
  );
}

export function ErrorState({ title, description, action }: FeedbackStateProps) {
  return (
    <div className="error-state">
      <span className="feedback-state-icon" aria-hidden="true">
        <AlertTriangle className="size-4" />
      </span>
      <div className="min-w-0">
        <strong>{title}</strong>
        {description ? <span>{description}</span> : null}
        {action ? <div className="feedback-action">{action}</div> : null}
      </div>
    </div>
  );
}
