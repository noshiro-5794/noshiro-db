import { Toast } from '@base-ui/react/toast';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { toastManager } from '@/shared/ui/toast';

function Toaster() {
  const { t } = useI18n();

  return (
    <Toast.Provider limit={4} timeout={5000} toastManager={toastManager}>
      <Toast.Portal>
        <Toast.Viewport className="fixed left-1/2 top-3 z-50 m-0 flex w-[min(24rem,calc(100vw-1.5rem))] -translate-x-1/2 flex-col gap-2 outline-none sm:top-4">
          <ToastList closeLabel={t('common.close')} />
        </Toast.Viewport>
      </Toast.Portal>
    </Toast.Provider>
  );
}

function ToastList({ closeLabel }: { closeLabel: string }) {
  const { toasts } = Toast.useToastManager();

  return toasts.map((item) => (
    <Toast.Root
      className="relative flex min-h-14 w-full items-start gap-3 rounded-sm border border-border bg-elevated p-3 pr-10 text-foreground shadow-[var(--ui-shadow-popup)] outline-none transition-[opacity,transform] duration-[var(--ui-transition-standard)] data-[ending-style]:-translate-y-2 data-[ending-style]:opacity-0 data-[starting-style]:-translate-y-2 data-[starting-style]:opacity-0 data-[type=error]:border-[color-mix(in_srgb,var(--ui-danger)_42%,var(--ui-border))] data-[type=success]:border-[color-mix(in_srgb,var(--ui-success)_34%,var(--ui-border))]"
      data-slot="toast"
      key={item.id}
      swipeDirection={['up', 'right']}
      toast={item}
    >
      <span
        className={cn(
          'mt-0.5 grid size-5 shrink-0 place-items-center text-[var(--ui-text-muted)]',
          item.type === 'success' && 'text-[var(--ui-success)]',
          item.type === 'error' && 'text-[var(--ui-danger)]',
        )}
      >
        {item.type === 'success' ? (
          <CheckCircle2 className="size-4" />
        ) : item.type === 'error' ? (
          <AlertTriangle className="size-4" />
        ) : (
          <Info className="size-4" />
        )}
      </span>
      <Toast.Content className="min-w-0 flex-1">
        <Toast.Title className="text-sm font-medium leading-5" />
        <Toast.Description className="mt-0.5 text-xs leading-5 text-[var(--ui-text-muted)]" />
      </Toast.Content>
      <Toast.Close
        aria-label={closeLabel}
        className="absolute right-2.5 top-2.5 grid size-7 place-items-center rounded-sm text-subtle-foreground outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
      >
        <X className="size-3.5" />
      </Toast.Close>
    </Toast.Root>
  ));
}

export { Toaster };
