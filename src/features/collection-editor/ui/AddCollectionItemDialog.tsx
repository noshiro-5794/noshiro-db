import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { libraryMutations, libraryQueries } from '@/entities/library';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { SearchField } from '@/shared/ui/DataView';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { toast } from '@/shared/ui/toast';
import { userSubjectImage, userSubjectSubtitle, userSubjectTitle } from '../model/presentation';
import { invalidateCollectionViews } from '../model/cache';

export function AddCollectionItemDialog({
  collectionId,
  itemCount,
  publicProfileUserId,
}: {
  collectionId: number;
  itemCount: number;
  publicProfileUserId: number;
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [keyword, setKeyword] = useState('');
  const searchQuery = useQuery({
    ...libraryQueries.userSubjects({
      ...(keyword.trim() ? { keyword: keyword.trim() } : {}),
      ordering: '-updated_at',
      page_size: 12,
    }),
    enabled: open,
  });
  const addMutation = useMutation({
    ...libraryMutations.addCollectionItem(),
    onError: () => toast.error(t('common.requestFailed')),
    onSuccess: async () => {
      await invalidateCollectionViews(queryClient, { userId: publicProfileUserId || undefined });
      toast.success(t('collections.addedItem'));
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button type="button" />}>
        <Plus className="size-4" />
        {t('collections.addFromLibrary')}
      </DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{t('collections.addFromLibraryTitle')}</DialogTitle>
          <DialogDescription>{t('collections.addFromLibraryDescription')}</DialogDescription>
        </DialogHeader>
        <div className="grid min-h-0 gap-4 overflow-y-auto">
          <SearchField
            aria-label={t('collections.librarySearchPlaceholder')}
            placeholder={t('collections.librarySearchPlaceholder')}
            value={keyword}
            onChange={(event) => {
              setKeyword(event.target.value);
            }}
          />
          {searchQuery.isLoading ? <LoadingState title={t('library.loading')} /> : null}
          {searchQuery.isError ? (
            <ErrorState title={t('library.errorTitle')} description={t('search.errorBody')} />
          ) : null}
          {(searchQuery.data?.results.length ?? 0) > 0 ? (
            <ul className="m-0 grid list-none gap-2 p-0">
              {(searchQuery.data?.results ?? []).map((item) => {
                const title = userSubjectTitle(item, t('common.untitledSubject'));
                const isAdding = addMutation.isPending && addMutation.variables.body.library_entry_id === item.id;

                return (
                  <li className="min-w-0" key={item.id}>
                    <article className="grid min-w-0 grid-cols-[48px_minmax(0,1fr)] items-center gap-x-3 gap-y-2 rounded-sm border border-border bg-surface p-2 sm:grid-cols-[48px_minmax(0,1fr)_auto]">
                      <img
                        alt=""
                        className="row-span-2 h-16 w-12 rounded-sm bg-muted object-cover ring-1 ring-inset ring-border-subtle sm:row-span-1"
                        decoding="async"
                        loading="lazy"
                        referrerPolicy="no-referrer"
                        src={userSubjectImage(item) || placeholderImagePaths.subjectCover}
                      />
                      <div className="col-start-2 row-start-1 min-w-0">
                        <h3 className="m-0 line-clamp-1 text-sm font-semibold text-foreground">{title}</h3>
                        <p className="m-0 mt-1 line-clamp-1 text-xs text-muted-foreground">
                          {userSubjectSubtitle(item, t('common.noMetadata'))}
                        </p>
                      </div>
                      <Button
                        aria-busy={isAdding || undefined}
                        aria-label={`${t('common.add')}: ${title}`}
                        className="col-start-2 row-start-2 max-w-full justify-self-start sm:col-start-3 sm:row-start-1 sm:justify-self-end"
                        disabled={addMutation.isPending}
                        size="sm"
                        type="button"
                        onClick={() => {
                          addMutation.mutate({
                            collectionId,
                            body: { library_entry_id: item.id, order: itemCount + 1 },
                          });
                        }}
                      >
                        <Plus aria-hidden="true" className="size-4" />
                        {isAdding ? t('common.saving') : t('common.add')}
                      </Button>
                    </article>
                  </li>
                );
              })}
            </ul>
          ) : null}
          {!searchQuery.isFetching && !searchQuery.isError && (searchQuery.data?.results.length ?? 0) === 0 ? (
            <EmptyState title={t('library.emptyTitle')} description={t('library.emptyBody')} />
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
