import type { ComponentProps, ReactNode } from 'react';
import { Dialog as BaseDialog } from '@base-ui/react/dialog';
import { X } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';

function Dialog(props: ComponentProps<typeof BaseDialog.Root>) {
  return <BaseDialog.Root data-slot="dialog" {...props} />;
}

function DialogTrigger(props: ComponentProps<typeof BaseDialog.Trigger>) {
  return <BaseDialog.Trigger data-slot="dialog-trigger" {...props} />;
}

type DialogContentProps = ComponentProps<typeof BaseDialog.Popup> & {
  closeLabel?: string;
  children?: ReactNode;
  placement?: 'center' | 'left';
};

function DialogContent({ children, className, closeLabel, placement = 'center', ...props }: DialogContentProps) {
  const { t } = useI18n();

  return (
    <BaseDialog.Portal>
      <BaseDialog.Backdrop
        className="fixed inset-0 z-50 bg-[var(--ui-overlay)] backdrop-blur-[2px] transition-opacity duration-[var(--ui-transition-standard)] data-[ending-style]:opacity-0 data-[starting-style]:opacity-0"
        data-slot="dialog-backdrop"
      />
      <BaseDialog.Viewport
        className={cn(
          'fixed inset-0 z-50 flex overflow-y-auto outline-none',
          placement === 'left' ? 'justify-start p-2 sm:p-3' : 'items-center justify-center p-4 sm:p-6',
        )}
        data-slot="dialog-viewport"
      >
        <BaseDialog.Popup
          className={cn(
            'relative grid w-full border border-control-border bg-elevated text-foreground shadow-[var(--ui-shadow-dialog)] outline-none transition-[opacity,transform] duration-[var(--ui-transition-standard)] data-[ending-style]:opacity-0 data-[starting-style]:opacity-0',
            placement === 'left'
              ? 'h-full max-w-[304px] grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden rounded-lg data-[ending-style]:-translate-x-2 data-[starting-style]:-translate-x-2'
              : 'max-h-[calc(100dvh-2rem)] max-w-lg gap-4 overflow-y-auto overscroll-contain rounded-md p-4 data-[ending-style]:scale-[0.985] data-[starting-style]:scale-[0.985] sm:p-5',
            className,
          )}
          data-slot="dialog-content"
          {...props}
        >
          {children}
          <BaseDialog.Close
            aria-label={closeLabel ?? t('common.close')}
            className="absolute right-3 top-3 grid size-7 place-items-center rounded-sm text-subtle-foreground outline-none transition-colors duration-[var(--ui-transition-fast)] hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-elevated"
            data-slot="dialog-close"
          >
            <X className="size-4" />
          </BaseDialog.Close>
        </BaseDialog.Popup>
      </BaseDialog.Viewport>
    </BaseDialog.Portal>
  );
}

function DialogHeader({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('grid gap-1 pr-8', className)} data-slot="dialog-header" {...props} />;
}

function DialogTitle({ className, ...props }: ComponentProps<typeof BaseDialog.Title>) {
  return (
    <BaseDialog.Title
      className={cn('text-base font-semibold leading-6 text-foreground', className)}
      data-slot="dialog-title"
      {...props}
    />
  );
}

function DialogDescription({ className, ...props }: ComponentProps<typeof BaseDialog.Description>) {
  return (
    <BaseDialog.Description
      className={cn('text-[13px] leading-5 text-muted-foreground', className)}
      data-slot="dialog-description"
      {...props}
    />
  );
}

function DialogFooter({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('flex flex-col-reverse gap-2 pt-1 sm:flex-row sm:items-center sm:justify-end', className)}
      data-slot="dialog-footer"
      {...props}
    />
  );
}

export { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger };
