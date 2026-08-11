import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';

type AppErrorBoundaryProps = {
  children: ReactNode;
  resetKey: string;
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

  override componentDidUpdate(previousProps: AppErrorBoundaryProps) {
    if (this.state.error && previousProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  override render() {
    if (this.state.error) {
      return (
        <AppErrorFallback
          onReset={() => {
            this.setState({ error: null });
          }}
        />
      );
    }

    return this.props.children;
  }
}

function AppErrorFallback({ onReset }: { onReset: () => void }) {
  const { t } = useI18n();

  return (
    <main className="grid min-h-[50vh] place-items-center px-6 py-16 text-[var(--ui-text)]">
      <section className="grid w-full max-w-lg justify-items-center text-center">
        <div className="grid size-12 place-items-center rounded-full border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)] text-[var(--ui-danger-text)]">
          <AlertTriangle className="size-5" />
        </div>
        <h1 className="mt-5 text-2xl font-semibold tracking-normal">{t('error.title')}</h1>
        <p className="mt-3 max-w-md text-sm leading-6 text-[var(--ui-text-muted)]">{t('error.description')}</p>
        <div className="mt-8">
          <Button type="button" variant="secondary" onClick={onReset}>
            <RotateCcw className="size-4" />
            {t('common.retry')}
          </Button>
        </div>
      </section>
    </main>
  );
}
