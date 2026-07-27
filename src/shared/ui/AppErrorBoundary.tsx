import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { Button } from '@/shared/ui/Button';

type AppErrorBoundaryProps = {
  children: ReactNode;
};

type AppErrorBoundaryState = {
  error: Error | null;
};

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  override state: AppErrorBoundaryState = {
    error: null,
  };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled React error', error, errorInfo);
  }

  override render() {
    if (this.state.error) {
      return (
        <main className="grid min-h-dvh place-items-center bg-[var(--color-bg)] px-6 py-16 text-[var(--color-text)]">
          <section className="grid w-full max-w-lg justify-items-center text-center">
            <div className="grid size-12 place-items-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text-muted)]">
              <AlertTriangle className="size-5" />
            </div>
            <p className="mt-6 text-xs font-semibold uppercase text-neutral-400">Application error</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Something went wrong</h1>
            <p className="mt-4 max-w-md text-sm leading-6 text-[var(--color-text-muted)]">
              The current view failed while rendering. Try reloading this view, or return to a stable route from the
              navigation.
            </p>
            <div className="mt-8">
              <Button type="button" variant="secondary" onClick={() => this.setState({ error: null })}>
                <RotateCcw className="size-4" />
                Try again
              </Button>
            </div>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
