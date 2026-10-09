import { type SyntheticEvent, useState } from 'react';
import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query';
import { PencilLine, Trash2 } from 'lucide-react';
import { communityMutations, communityQueryKeys } from '@/entities/community';
import type { CommunityCommentSummary, CommunityTargetType } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { CheckboxField } from '@/shared/ui/Checkbox';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { Textarea } from '@/shared/ui/Textarea';
import { toast } from '@/shared/ui/toast';
import { CommunityReportDialog } from './CommunityReportDialog';

type CommentTargetType = Extract<CommunityTargetType, 'post' | 'review' | 'collection' | 'activity'>;

type CommentMutationDialogsProps = {
  deleteTarget: CommunityCommentSummary | null;
  editTarget: CommunityCommentSummary | null;
  reportTarget: CommunityCommentSummary | null;
  targetId: number;
  targetType: CommentTargetType;
  onCloseDelete: () => void;
  onCloseEdit: () => void;
  onCloseReport: () => void;
  onDeleted: (comment: CommunityCommentSummary) => void | Promise<void>;
};

type DialogProps = {
  commentQueryKey: QueryKey;
  target: CommunityCommentSummary;
  onClose: () => void;
};

function EditCommentDialog({ commentQueryKey, target, onClose }: DialogProps) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [content, setContent] = useState(target.content);
  const [isSpoiler, setIsSpoiler] = useState(target.is_spoiler);
  const mutation = useMutation({
    ...communityMutations.updateComment(),
    onError: () => {
      toast.error(t('common.requestFailed'));
    },
    onSuccess: async () => {
      onClose();
      await queryClient.invalidateQueries({ queryKey: commentQueryKey });
    },
  });

  function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (mutation.isPending || !content.trim()) return;
    mutation.mutate({
      commentId: target.id,
      body: { content, is_spoiler: isSpoiler },
    });
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('community.editCommentTitle')}</DialogTitle>
          <DialogDescription>{t('community.editCommentDescription')}</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={submit}>
          <Textarea
            aria-label={t('community.commentPlaceholder')}
            className="min-h-40"
            maxLength={5_000}
            value={content}
            placeholder={t('community.commentPlaceholder')}
            onChange={(event) => {
              setContent(event.target.value);
            }}
          />
          <CheckboxField checked={isSpoiler} onCheckedChange={setIsSpoiler}>
            {t('community.markSpoiler')}
          </CheckboxField>
          <DialogFooter>
            <Button type="button" variant="secondary" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button disabled={mutation.isPending || !content.trim()} type="submit">
              <PencilLine className="size-4" /> {t('common.save')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function DeleteCommentDialog({
  target,
  onClose,
  onDeleted,
}: Omit<DialogProps, 'commentQueryKey'> & {
  onDeleted: (comment: CommunityCommentSummary) => void | Promise<void>;
}) {
  const { t } = useI18n();
  const mutation = useMutation({
    ...communityMutations.deleteComment(),
    onError: () => {
      toast.error(t('common.requestFailed'));
    },
    onSuccess: async () => {
      onClose();
      await onDeleted(target);
    },
  });

  return (
    <ConfirmDialog
      confirmIcon={<Trash2 className="size-4" />}
      confirmLabel={t('common.delete')}
      description={t('community.deleteCommentBody')}
      isPending={mutation.isPending}
      open
      title={t('community.deleteCommentTitle')}
      onConfirm={() => {
        if (!mutation.isPending) mutation.mutate(target.id);
      }}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
    />
  );
}

export function CommentMutationDialogs({
  deleteTarget,
  editTarget,
  reportTarget,
  targetId,
  targetType,
  onCloseDelete,
  onCloseEdit,
  onCloseReport,
  onDeleted,
}: CommentMutationDialogsProps) {
  const { t } = useI18n();
  const commentQueryKey = communityQueryKeys.commentTarget(targetType, targetId);

  return (
    <>
      {deleteTarget ? (
        <DeleteCommentDialog target={deleteTarget} onClose={onCloseDelete} onDeleted={onDeleted} />
      ) : null}
      {editTarget ? (
        <EditCommentDialog
          commentQueryKey={commentQueryKey}
          key={editTarget.id}
          target={editTarget}
          onClose={onCloseEdit}
        />
      ) : null}
      {reportTarget ? (
        <CommunityReportDialog
          label={t('community.reportComment')}
          open
          targetId={reportTarget.id}
          targetType="comment"
          onOpenChange={(open) => {
            if (!open) onCloseReport();
          }}
        />
      ) : null}
    </>
  );
}
