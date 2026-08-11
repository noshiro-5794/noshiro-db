import { type SyntheticEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Flag } from 'lucide-react';
import { communityMutations } from '@/entities/community';
import type { CommunityReportReason, CommunityTargetType } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { Textarea } from '@/shared/ui/Textarea';
import { toast } from '@/shared/ui/toast';
import { ReportReasonPicker } from './ReportReasonPicker';

type CommunityReportDialogProps = {
  label: string;
  open: boolean;
  targetId: number;
  targetType: CommunityTargetType;
  onOpenChange: (open: boolean) => void;
};

function CommunityReportDialogContent({
  label,
  targetId,
  targetType,
  onClose,
}: Omit<CommunityReportDialogProps, 'open' | 'onOpenChange'> & { onClose: () => void }) {
  const { t } = useI18n();
  const [reason, setReason] = useState<CommunityReportReason>('spam');
  const [description, setDescription] = useState('');
  const mutation = useMutation({
    ...communityMutations.createReport(),
    onError: () => {
      toast.error(t('common.requestFailed'));
    },
    onSuccess: onClose,
  });

  function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (mutation.isPending) return;
    mutation.mutate({ target_type: targetType, target_id: targetId, reason, description });
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{t('community.reportTitle')}</DialogTitle>
        <DialogDescription>{label || t('community.reportDescription')}</DialogDescription>
      </DialogHeader>
      <form className="grid gap-4" onSubmit={submit}>
        <ReportReasonPicker value={reason} onValueChange={setReason} />
        <Textarea
          aria-label={t('community.reportPlaceholder')}
          className="min-h-28"
          maxLength={2_000}
          value={description}
          placeholder={t('community.reportPlaceholder')}
          onChange={(event) => {
            setDescription(event.target.value);
          }}
        />
        <DialogFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button disabled={mutation.isPending} type="submit">
            <Flag className="size-4" /> {t('community.submitReport')}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  );
}

export function CommunityReportDialog({ label, open, targetId, targetType, onOpenChange }: CommunityReportDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open ? (
        <CommunityReportDialogContent
          label={label}
          targetId={targetId}
          targetType={targetType}
          onClose={() => {
            onOpenChange(false);
          }}
        />
      ) : null}
    </Dialog>
  );
}
