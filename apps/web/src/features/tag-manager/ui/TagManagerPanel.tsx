import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Tag as TagIcon, Trash2, X } from 'lucide-react';
import { libraryMutations, libraryQueryKeys } from '@/entities/library';
import type { Tag } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { ErrorState } from '@/shared/ui/FeedbackState';
import { FilterPanel, FilterPanelHeader, FilterTag } from '@/shared/ui/FilterPanel';
import { toast } from '@/shared/ui/toast';

export function TagManagerPanel({
  isError,
  isLoading,
  selectedTagId,
  tags,
  onSelectTag,
}: {
  isError: boolean;
  isLoading: boolean;
  selectedTagId: number | null;
  tags: Tag[];
  onSelectTag: (tagId: number | null) => void;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<Tag | null>(null);
  const deleteMutation = useMutation({
    ...libraryMutations.deleteTag(),
    onError: () => toast.error(t('common.requestFailed')),
    onSuccess: async (_data, deletedTagId) => {
      setDeleteTarget(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.tags() }),
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.userSubjects() }),
      ]);
      if (selectedTagId === deletedTagId) onSelectTag(null);
    },
  });

  return (
    <>
      <FilterPanel>
        <FilterPanelHeader>
          <TagIcon className="size-4 text-[var(--ui-text-subtle)]" />
          <h2>{t('library.tags')}</h2>
        </FilterPanelHeader>
        {isError ? <ErrorState title={t('library.errorTitle')} /> : null}
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => {
            const isSelected = selectedTagId === tag.id;
            return (
              <FilterTag active={isSelected} key={tag.id}>
                <Button
                  className="px-3 py-1.5 transition hover:bg-[var(--ui-bg-surface)]/60"
                  type="button"
                  variant="unstyled"
                  onClick={() => {
                    onSelectTag(isSelected ? null : tag.id);
                  }}
                >
                  {tag.name}
                </Button>
                <Button
                  aria-label={`${t('common.delete')} ${tag.name}`}
                  className="grid size-8 place-items-center border-l border-current/10 transition hover:bg-[var(--ui-bg-surface)]/70"
                  type="button"
                  variant="unstyled"
                  onClick={() => {
                    setDeleteTarget(tag);
                  }}
                >
                  <X className="size-3.5" />
                </Button>
              </FilterTag>
            );
          })}
          {!isLoading && !isError && tags.length === 0 ? (
            <span className="text-sm text-[var(--ui-text-muted)]">{t('library.noTags')}</span>
          ) : null}
        </div>
      </FilterPanel>

      <ConfirmDialog
        confirmDisabled={!deleteTarget}
        confirmIcon={<Trash2 className="size-4" />}
        confirmLabel={t('common.delete')}
        description={`${t('library.deleteTagBody')}${deleteTarget ? ` "${deleteTarget.name}"` : ''}`}
        isPending={deleteMutation.isPending}
        open={Boolean(deleteTarget)}
        title={t('library.deleteTagTitle')}
        onConfirm={() => {
          if (deleteTarget && !deleteMutation.isPending) deleteMutation.mutate(deleteTarget.id);
        }}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setDeleteTarget(null);
        }}
      />
    </>
  );
}
