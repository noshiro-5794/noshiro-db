import { useRouter, type ErrorComponentProps } from '@tanstack/react-router';
import { AlertTriangle, Home, RotateCcw } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { Button } from './Button';

export function RouteErrorState({ reset }: ErrorComponentProps) {
  const { t } = useI18n();
  const router = useRouter();

  return (
    <section className="grid min-h-[50vh] place-items-center px-6 py-16 text-[var(--ui-text)]">
      <div className="grid w-full max-w-lg justify-items-center text-center">
        <div className="grid size-12 place-items-center rounded-full border border-[var(--ui-border)] bg-[var(--ui-bg-subtle)] text-[var(--ui-danger-text)]">
          <AlertTriangle className="size-5" />
        </div>
        <h1 className="mt-5 text-2xl font-semibold tracking-normal">{t('error.title')}</h1>
        <p className="mt-3 max-w-md text-sm leading-6 text-[var(--ui-text-muted)]">{t('error.description')}</p>
        <div className="mt-7 flex flex-wrap justify-center gap-2">
          <Button type="button" onClick={reset}>
            <RotateCcw className="size-4" />
            {t('common.retry')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              reset();
              void router.navigate({ to: '/' });
            }}
          >
            <Home className="size-4" />
            {t('nav.home')}
          </Button>
        </div>
      </div>
    </section>
  );
}
