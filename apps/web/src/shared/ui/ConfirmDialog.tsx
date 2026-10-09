import type { ReactNode } from 'react';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';

type ConfirmDialogProps = {
  confirmDisabled?: boolean;
  confirmIcon?: ReactNode;
  confirmLabel: string;
  description: ReactNode;
  details?: ReactNode;
  isPending?: boolean;
  open: boolean;
  title: ReactNode;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
};

export function ConfirmDialog({
  confirmDisabled = false,
  confirmIcon,
  confirmLabel,
  description,
  details,
  isPending = false,
  open,
  title,
  onConfirm,
  onOpenChange,
}: ConfirmDialogProps) {
  const { t } = useI18n();

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!isPending) onOpenChange(nextOpen);
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {details}
        <DialogFooter data-slot="confirm-dialog-actions">
          <Button
            disabled={isPending}
            type="button"
            variant="secondary"
            onClick={() => {
              onOpenChange(false);
            }}
          >
            {t('common.cancel')}
          </Button>
          <Button disabled={isPending || confirmDisabled} type="button" variant="destructive" onClick={onConfirm}>
            {confirmIcon}
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
