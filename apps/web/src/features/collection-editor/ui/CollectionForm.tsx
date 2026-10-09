import { type SyntheticEvent, useId } from 'react';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { DialogFooter } from '@/shared/ui/Dialog';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { Input } from '@/shared/ui/Input';
import { Switch } from '@/shared/ui/Switch';
import { Textarea } from '@/shared/ui/Textarea';
import { CollectionRatingStars } from './CollectionRatingStars';
import type { CollectionDraft } from '../model/draft';

export function CollectionForm({
  draft,
  isPending,
  submitLabel,
  onCancel,
  onChange,
  onSubmit,
}: {
  draft: CollectionDraft;
  isPending: boolean;
  submitLabel: string;
  onCancel: () => void;
  onChange: (draft: CollectionDraft) => void;
  onSubmit: (event: SyntheticEvent<HTMLFormElement, SubmitEvent>) => void;
}) {
  const { t } = useI18n();
  const nameId = useId();
  const noteId = useId();
  const visibilityLabelId = useId();

  return (
    <form aria-busy={isPending} className="grid gap-4" onSubmit={onSubmit}>
      <Field>
        <FieldLabel htmlFor={nameId}>{t('collections.name')}</FieldLabel>
        <Input
          required
          id={nameId}
          maxLength={256}
          name="name"
          value={draft.name}
          placeholder={t('collections.namePlaceholder')}
          onChange={(event) => {
            onChange({ ...draft, name: event.target.value });
          }}
        />
      </Field>
      <Field>
        <FieldLabel htmlFor={noteId}>{t('collections.note')}</FieldLabel>
        <Textarea
          className="min-h-28"
          id={noteId}
          maxLength={5_000}
          name="note"
          value={draft.note}
          placeholder={t('collections.notePlaceholder')}
          onChange={(event) => {
            onChange({ ...draft, note: event.target.value });
          }}
        />
      </Field>
      <div className="divide-y divide-border-subtle rounded-sm bg-muted px-3">
        <fieldset className="flex min-w-0 items-center justify-between gap-4 py-2.5">
          <legend className="sr-only">{t('collections.rating')}</legend>
          <CollectionRatingStars
            interactive
            ariaLabel={t('collections.rating')}
            label={t('common.unrated')}
            value={draft.rating}
            onChange={(rating) => {
              onChange({ ...draft, rating });
            }}
          />
        </fieldset>
        <div className="flex items-center justify-between gap-4 py-2.5 text-[13px] font-medium text-foreground">
          <span id={visibilityLabelId}>
            {draft.isPublic ? t('collections.publicCollection') : t('collections.privateCollection')}
          </span>
          <Switch
            aria-labelledby={visibilityLabelId}
            checked={draft.isPublic}
            onCheckedChange={(isPublic) => {
              onChange({ ...draft, isPublic });
            }}
          />
        </div>
      </div>
      <DialogFooter>
        <Button disabled={isPending} type="button" variant="secondary" onClick={onCancel}>
          {t('common.cancel')}
        </Button>
        <Button disabled={isPending || !draft.name.trim()} type="submit">
          {submitLabel}
        </Button>
      </DialogFooter>
    </form>
  );
}
