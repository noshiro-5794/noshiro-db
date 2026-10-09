import { Trash2 } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';

export function ReviewDeleteDialog({
  isPending,
  open,
  reviewTitle,
  onConfirm,
  onOpenChange,
}: {
  isPending: boolean;
  open: boolean;
  reviewTitle?: string | undefined;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
}) {
  const { t } = useI18n();

  return (
    <ConfirmDialog
      confirmIcon={<Trash2 className="size-4" />}
      confirmLabel={t('common.delete')}
      description={`${t('reviewViewer.deleteBody')}${reviewTitle ? ` ${reviewTitle}` : ''}`}
      isPending={isPending}
      open={open}
      title={t('reviewViewer.deleteTitle')}
      onConfirm={onConfirm}
      onOpenChange={onOpenChange}
    />
  );
}
