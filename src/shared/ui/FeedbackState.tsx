import type { ReactNode } from 'react';

type FeedbackStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: FeedbackStateProps) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      {description ? <span>{description}</span> : null}
      {action ? <div className="feedback-action">{action}</div> : null}
    </div>
  );
}

export function LoadingState({ title, description }: FeedbackStateProps) {
  return (
    <div className="loading-state">
      <span className="loading-indicator" aria-hidden="true" />
      <strong>{title}</strong>
      {description ? <span>{description}</span> : null}
    </div>
  );
}

export function ErrorState({ title, description, action }: FeedbackStateProps) {
  return (
    <div className="empty-state error-state">
      <strong>{title}</strong>
      {description ? <span>{description}</span> : null}
      {action ? <div className="feedback-action">{action}</div> : null}
    </div>
  );
}
