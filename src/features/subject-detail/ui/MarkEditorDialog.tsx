import { type SyntheticEvent, useId, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Check, Trash2 } from 'lucide-react';
import { libraryMutations, libraryQueryKeys } from '@/entities/library';
import type { ProgressSummary, UUID, UserSubjectContext } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { Input } from '@/shared/ui/Input';
import { Switch } from '@/shared/ui/Switch';
import { Textarea } from '@/shared/ui/Textarea';
import { toast } from '@/shared/ui/toast';
import { createMarkDraft, parseMarkDraft } from '../model/mark-draft';
import { saveMarkChanges } from '../model/save-mark';
import { MarkMetadataFields, MarkStatusPicker, type DraftRatingDetail } from './MarkFormFields';
import { StarRatingControl } from './RatingStars';

export function MarkEditorDialog({
  context,
  open,
  subjectId,
  totalEpisodeCount,
  onOpenChange,
}: {
  context: UserSubjectContext | undefined;
  open: boolean;
  subjectId: UUID;
  totalEpisodeCount: number;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open ? (
        <MarkEditorContent
          context={context}
          subjectId={subjectId}
          totalEpisodeCount={totalEpisodeCount}
          onClose={() => {
            onOpenChange(false);
          }}
        />
      ) : null}
    </Dialog>
  );
}

function MarkEditorContent({
  context,
  subjectId,
  totalEpisodeCount,
  onClose,
}: {
  context: UserSubjectContext | undefined;
  subjectId: UUID;
  totalEpisodeCount: number;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const formId = useId();
  const commentId = useId();
  const ratingId = useId();
  const visibilityId = useId();
  const initialDraft = createMarkDraft(context);
  const operationInFlight = useRef(false);
  const [status, setStatus] = useState(initialDraft.status);
  const [simpleRating, setSimpleRating] = useState(initialDraft.simpleRating);
  const [rating, setRating] = useState(initialDraft.rating);
  const [comment, setComment] = useState(initialDraft.comment);
  const [isPublic, setIsPublic] = useState(initialDraft.isPublic);
  const [tagText, setTagText] = useState(initialDraft.tagText);
  const [ratingDetails, setRatingDetails] = useState<DraftRatingDetail[]>(
    initialDraft.ratingDetails.map((detail, index) => ({ ...detail, id: index + 1 })),
  );
  const [errorMessage, setErrorMessage] = useState('');
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const createMutation = useMutation(libraryMutations.createUserSubject());
  const updateMutation = useMutation(libraryMutations.updateUserSubject());
  const deleteMutation = useMutation(libraryMutations.deleteUserSubject());
  const replaceTagsMutation = useMutation(libraryMutations.replaceTags());
  const replaceDetailsMutation = useMutation(libraryMutations.replaceRatingDetails());
  const userSubject = context?.user_subject ?? null;
  const isBusy =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending ||
    replaceTagsMutation.isPending ||
    replaceDetailsMutation.isPending;

  async function refreshContext() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.subjectContext(subjectId) }),
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.progress(subjectId) }),
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.userSubjects() }),
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.tags() }),
    ]);
  }

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (operationInFlight.current) return;
    setErrorMessage('');
    const parsed = parseMarkDraft({
      status,
      simpleRating,
      rating,
      comment,
      isPublic,
      tagText,
      ratingDetails: ratingDetails.map(({ key, value }) => ({ key, value })),
    });
    if (!parsed) {
      setErrorMessage(t('subject.invalidMarkForm'));
      return;
    }

    operationInFlight.current = true;
    try {
      await saveMarkChanges(
        { subjectId, userSubjectId: userSubject?.id ?? null, draft: parsed },
        {
          create: createMutation.mutateAsync,
          update: updateMutation.mutateAsync,
          replaceTags: replaceTagsMutation.mutateAsync,
          replaceRatingDetails: replaceDetailsMutation.mutateAsync,
          refresh: refreshContext,
        },
      );
      toast.success(t(userSubject ? 'subject.markUpdated' : 'subject.markCreated'));
      onClose();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('common.requestFailed'));
    } finally {
      operationInFlight.current = false;
    }
  }

  async function handleDelete() {
    if (!userSubject || operationInFlight.current) return;
    operationInFlight.current = true;
    setErrorMessage('');
    try {
      await deleteMutation.mutateAsync(userSubject.id);
      queryClient.setQueryData<ProgressSummary>(libraryQueryKeys.progress(subjectId), {
        subject_id: subjectId,
        user_subject_id: null,
        total_episodes: totalEpisodeCount,
        finished_count: 0,
        finished_episode_ids: [],
        episodes: [],
      });
      await refreshContext();
      toast.success(t('subject.markDeleted'));
      setIsDeleteConfirmOpen(false);
      onClose();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t('common.requestFailed'));
      setIsDeleteConfirmOpen(false);
    } finally {
      operationInFlight.current = false;
    }
  }

  return (
    <>
      <DialogContent className="grid max-w-2xl grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden p-0">
        <DialogHeader className="px-5 pb-4 pt-5 pr-12">
          <DialogTitle>{userSubject ? t('subject.editMark') : t('subject.markSubject')}</DialogTitle>
        </DialogHeader>
        <div className="min-h-0 overflow-y-auto px-5 pb-5">
          <form aria-busy={isBusy} className="grid gap-4" id={formId} onSubmit={(event) => void handleSubmit(event)}>
            <MarkStatusPicker status={status} onChange={setStatus} />
            <div className="grid gap-4 sm:grid-cols-2">
              <fieldset className="grid min-w-0 gap-2">
                <legend className="mb-2 text-[13px] font-medium leading-5 text-foreground">
                  {t('subject.simple')}
                </legend>
                <StarRatingControl
                  clearLabel={t('common.clear')}
                  label={t('subject.simple')}
                  value={simpleRating}
                  onChange={setSimpleRating}
                />
              </fieldset>
              <Field>
                <FieldLabel htmlFor={ratingId}>{t('subject.rating')}</FieldLabel>
                <Input
                  id={ratingId}
                  inputMode="decimal"
                  maxLength={4}
                  placeholder="0.0 - 10.0"
                  value={rating}
                  onChange={(event) => {
                    setRating(event.target.value);
                  }}
                />
              </Field>
            </div>
            <Field>
              <FieldLabel htmlFor={commentId}>{t('subject.comment')}</FieldLabel>
              <Textarea
                id={commentId}
                maxLength={2_000}
                value={comment}
                onChange={(event) => {
                  setComment(event.target.value);
                }}
              />
            </Field>
            <div className="flex items-center justify-between gap-4 rounded-sm bg-muted px-3 py-2.5">
              <label className="text-[13px] font-medium text-foreground" htmlFor={visibilityId}>
                {t('subject.publicVisibility')}
              </label>
              <Switch id={visibilityId} checked={isPublic} onCheckedChange={setIsPublic} />
            </div>
            <MarkMetadataFields
              ratingDetails={ratingDetails}
              tagText={tagText}
              onRatingDetailsChange={setRatingDetails}
              onTagTextChange={setTagText}
            />
            {errorMessage ? (
              <p
                className="rounded-sm border border-[color-mix(in_srgb,var(--ui-danger)_24%,var(--ui-border))] bg-[var(--ui-danger-soft)] px-3 py-2 text-sm text-[var(--ui-danger-text)]"
                role="alert"
              >
                {errorMessage}
              </p>
            ) : null}
          </form>
        </div>
        <DialogFooter className="bg-[color-mix(in_srgb,var(--ui-bg-subtle)_52%,transparent)] px-5 py-3">
          {userSubject ? (
            <Button
              className="text-destructive hover:bg-[var(--ui-danger-soft)] hover:text-destructive sm:mr-auto"
              disabled={isBusy}
              type="button"
              variant="ghost"
              onClick={() => {
                setIsDeleteConfirmOpen(true);
              }}
            >
              <Trash2 className="size-4" />
              {t('subject.deleteMark')}
            </Button>
          ) : null}
          <Button
            className="w-full sm:ml-auto sm:w-auto"
            disabled={isBusy}
            type="button"
            variant="secondary"
            onClick={onClose}
          >
            {t('common.cancel')}
          </Button>
          <Button className="w-full sm:w-auto" disabled={isBusy} form={formId} type="submit">
            <Check className="size-4" />
            {isBusy ? t('common.saving') : userSubject ? t('subject.saveMark') : t('subject.markSubject')}
          </Button>
        </DialogFooter>
      </DialogContent>

      <ConfirmDialog
        confirmIcon={<Trash2 className="size-4" />}
        confirmLabel={t('common.delete')}
        description={t('subject.deleteMarkBody')}
        details={
          <div className="rounded-sm border border-[color-mix(in_srgb,var(--ui-danger)_28%,var(--ui-border))] bg-[var(--ui-danger-soft)] p-3 text-sm text-[var(--ui-danger-text)]">
            <AlertTriangle className="mr-2 inline size-4" />
            {t('subject.deleteMarkWarning')}
          </div>
        }
        isPending={isBusy}
        open={isDeleteConfirmOpen}
        title={t('subject.deleteMarkTitle')}
        onConfirm={() => void handleDelete()}
        onOpenChange={setIsDeleteConfirmOpen}
      />
    </>
  );
}
