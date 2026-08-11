import { useId, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check, Eye, Heart, Pause, Plus, Trash2, XCircle } from 'lucide-react';
import { libraryQueries } from '@/entities/library';
import type { RatingDetail } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { Field, FieldLabel } from '@/shared/ui/Field';
import { Input } from '@/shared/ui/Input';
import { Toggle, ToggleGroup } from '@/shared/ui/Toggle';
import { isMarkStatus, type MarkStatus } from '../model/mark-draft';

export type DraftRatingDetail = RatingDetail & { id: number };

const statusIcons: Record<MarkStatus, typeof Heart> = {
  wish: Heart,
  doing: Eye,
  done: Check,
  on_hold: Pause,
  drop: XCircle,
};

export function MarkStatusPicker({ status, onChange }: { status: MarkStatus; onChange: (status: MarkStatus) => void }) {
  const { t } = useI18n();
  const labelId = useId();
  const options = [
    { label: t('status.wish'), value: 'wish' },
    { label: t('status.doing'), value: 'doing' },
    { label: t('status.done'), value: 'done' },
    { label: t('status.onHold'), value: 'on_hold' },
    { label: t('status.drop'), value: 'drop' },
  ] satisfies Array<{ label: string; value: MarkStatus }>;

  return (
    <fieldset className="grid min-w-0 gap-2">
      <legend className="mb-2 text-[13px] font-medium leading-5 text-foreground" id={labelId}>
        {t('subject.status')}
      </legend>
      <ToggleGroup
        aria-labelledby={labelId}
        className="grid w-full grid-cols-2 gap-1 border-0 bg-transparent p-0 sm:grid-cols-5"
        value={[status]}
        onValueChange={(values) => {
          const nextStatus = values[0];
          if (isMarkStatus(nextStatus)) onChange(nextStatus);
        }}
      >
        {options.map((option) => {
          const StatusIcon = statusIcons[option.value];
          return (
            <Toggle
              className="group/status flex h-9 min-w-0 items-center justify-start gap-2 rounded-sm border border-transparent px-2.5 text-left text-[13px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground data-[pressed]:border-[var(--ui-accent-border)] data-[pressed]:bg-[var(--ui-accent-soft)] data-[pressed]:text-foreground"
              key={option.value}
              value={option.value}
              variant="bare"
            >
              <StatusIcon className="size-4 shrink-0 text-subtle-foreground transition-colors group-data-[pressed]/status:text-[var(--ui-accent-text)]" />
              <span className="min-w-0 truncate">{option.label}</span>
            </Toggle>
          );
        })}
      </ToggleGroup>
    </fieldset>
  );
}

export function MarkMetadataFields({
  ratingDetails,
  tagText,
  onRatingDetailsChange,
  onTagTextChange,
}: {
  ratingDetails: DraftRatingDetail[];
  tagText: string;
  onRatingDetailsChange: (details: DraftRatingDetail[]) => void;
  onTagTextChange: (value: string) => void;
}) {
  const { t } = useI18n();
  const tagsQuery = useQuery(libraryQueries.tags());
  const fieldIdPrefix = useId();
  const tagsId = useId();
  const nextRowId = useRef(Math.max(0, ...ratingDetails.map(({ id }) => id)) + 1);

  return (
    <>
      <section className="grid gap-3 pt-1">
        <Field>
          <FieldLabel htmlFor={tagsId}>{t('subject.tags')}</FieldLabel>
          <Input
            id={tagsId}
            value={tagText}
            onChange={(event) => {
              onTagTextChange(event.target.value);
            }}
          />
        </Field>
        <div className="flex flex-wrap gap-2">
          {(tagsQuery.data?.results ?? []).slice(0, 8).map((tag) => (
            <Button
              key={tag.id}
              size="xs"
              type="button"
              variant="secondary"
              onClick={() => {
                const tags = tagText
                  .split(',')
                  .map((item) => item.trim())
                  .filter(Boolean);
                if (!tags.includes(tag.name)) onTagTextChange([...tags, tag.name].join(', '));
              }}
            >
              {tag.name}
            </Button>
          ))}
        </div>
      </section>
      <fieldset className="grid min-w-0 gap-3 pt-1">
        <legend className="mb-2 text-[13px] font-medium leading-5 text-foreground">{t('subject.ratingDetails')}</legend>
        <div className="grid gap-2">
          {ratingDetails.map((detail, index) => {
            const detailKeyId = `${fieldIdPrefix}-key-${detail.id}`;
            const detailValueId = `${fieldIdPrefix}-value-${detail.id}`;
            const rowLabel = `${t('subject.ratingDetails')} ${index + 1}`;

            return (
              <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_32px]" key={detail.id}>
                <Field>
                  <FieldLabel className="sr-only" htmlFor={detailKeyId}>
                    {rowLabel} - {t('subject.ratingDetailName')}
                  </FieldLabel>
                  <Input
                    id={detailKeyId}
                    maxLength={256}
                    placeholder={t('subject.ratingDetailName')}
                    value={detail.key}
                    onChange={(event) => {
                      onRatingDetailsChange(
                        ratingDetails.map((row) => (row.id === detail.id ? { ...row, key: event.target.value } : row)),
                      );
                    }}
                  />
                </Field>
                <Field>
                  <FieldLabel className="sr-only" htmlFor={detailValueId}>
                    {rowLabel} - {t('subject.ratingDetailValue')}
                  </FieldLabel>
                  <Input
                    id={detailValueId}
                    inputMode="decimal"
                    maxLength={4}
                    placeholder={t('subject.ratingDetailValue')}
                    value={detail.value}
                    onChange={(event) => {
                      onRatingDetailsChange(
                        ratingDetails.map((row) =>
                          row.id === detail.id ? { ...row, value: event.target.value } : row,
                        ),
                      );
                    }}
                  />
                </Field>
                <Button
                  aria-label={`${t('common.delete')} ${rowLabel}`}
                  className="justify-self-end self-end"
                  disabled={ratingDetails.length <= 1}
                  size="icon-sm"
                  tooltip={t('common.delete')}
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    onRatingDetailsChange(ratingDetails.filter((row) => row.id !== detail.id));
                  }}
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
            );
          })}
        </div>
        <Button
          className="w-fit"
          disabled={ratingDetails.length >= 100}
          type="button"
          variant="secondary"
          onClick={() => {
            const id = nextRowId.current;
            nextRowId.current += 1;
            onRatingDetailsChange([...ratingDetails, { id, key: '', value: '' }]);
          }}
        >
          <Plus className="size-4" />
          {t('subject.addDetail')}
        </Button>
      </fieldset>
    </>
  );
}
