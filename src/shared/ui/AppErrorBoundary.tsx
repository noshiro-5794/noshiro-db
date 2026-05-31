import { Component, type ErrorInfo, type ReactNode } from 'react';
import { ErrorState } from '@/shared/ui/FeedbackState';

type AppErrorBoundaryProps = {
  children: ReactNode;
};

type AppErrorBoundaryState = {
  error: Error | null;
};

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = {
    error: null,
  };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled React error', error, errorInfo);
  }

  render() {
    if (this.state.error) {
      return (
        <ErrorState
          title="Something went wrong."
          description="The page crashed while rendering. Refresh the page or go back to a stable route."
          action={
            <button className="button button-secondary" type="button" onClick={() => this.setState({ error: null })}>
              Try again
            </button>
          }
        />
      );
    }

    return this.props.children;
  }
}
