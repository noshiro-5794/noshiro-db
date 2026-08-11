import { type SyntheticEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { libraryMutations } from '@/entities/library';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/shared/ui/Dialog';
import { toast } from '@/shared/ui/toast';
import { emptyCollectionDraft } from '../model/draft';
import { invalidateCollectionViews } from '../model/cache';
import { CollectionForm } from './CollectionForm';

export function CreateCollectionDialog({
  publicProfileUserId,
  onCreated,
}: {
  publicProfileUserId: number;
  onCreated: (collectionId: number) => void;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(emptyCollectionDraft);
  const createMutation = useMutation({
    ...libraryMutations.createCollection(),
    onError: () => toast.error(t('common.requestFailed')),
    onSuccess: async (collection) => {
      setDraft(emptyCollectionDraft());
      setOpen(false);
      await invalidateCollectionViews(queryClient, { userId: publicProfileUserId || undefined });
      onCreated(collection.id);
      toast.success(t('collections.created'));
    },
  });

  function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const name = draft.name.trim();
    if (!name || createMutation.isPending) return;

    createMutation.mutate({
      name,
      note: draft.note.trim(),
      ...(draft.rating === null ? {} : { simple_rating: draft.rating }),
      is_public: draft.isPublic,
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button type="button" />}>
        <Plus className="size-4" />
        {t('collections.new')}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('collections.createTitle')}</DialogTitle>
          <DialogDescription>{t('collections.createDescription')}</DialogDescription>
        </DialogHeader>
        <CollectionForm
          draft={draft}
          isPending={createMutation.isPending}
          submitLabel={t('collections.createAction')}
          onCancel={() => {
            setOpen(false);
          }}
          onChange={setDraft}
          onSubmit={submit}
        />
      </DialogContent>
    </Dialog>
  );
}
