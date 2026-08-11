import { useId, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { subjectQueries } from '@/entities/subject';
import type { SubjectCharacter, SubjectStaff, UUID } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Button } from '@/shared/ui/Button';
import { DetailSection } from '@/shared/ui/Detail';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Pagination } from '@/shared/ui/Pagination';
import { coverPlaceholder, detailRows, getInfoboxRows } from '../model/subject-detail';
import { DetailShell, StaffDetail, type StaffDetailLabels } from './SubjectDetailPrimitives';

const pageSize = 8;

export function CharactersSection({ className, subjectId }: { className?: string; subjectId: UUID }) {
  const { t } = useI18n();
  const emptyText = t('common.none');
  const sectionTitleId = useId();
  const [page, setPage] = useState(1);
  const [character, setCharacter] = useState<SubjectCharacter | null>(null);
  const [staff, setStaff] = useState<SubjectStaff | null>(null);
  const query = useQuery(subjectQueries.characters(subjectId, { page, page_size: pageSize }));
  const characterRows = query.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((query.data?.count ?? 0) / pageSize));
  const staffLabels: StaffDetailLabels = {
    type: t('subject.type'),
    gender: t('subject.gender'),
    birth: t('subject.birth'),
    career: t('subject.career'),
  };

  return (
    <>
      <DetailSection
        className={className}
        id="characters"
        meta={query.data ? `${query.data.count} ${t('common.items')}` : undefined}
        title={t('subject.characters')}
        titleId={sectionTitleId}
      >
        {query.isLoading && characterRows.length === 0 ? <LoadingState title={t('subject.characters')} /> : null}
        {query.isError ? (
          <ErrorState
            action={
              <Button size="sm" variant="secondary" onClick={() => void query.refetch()}>
                {t('common.retry')}
              </Button>
            }
            description={t('common.requestFailed')}
            title={t('subject.characters')}
          />
        ) : null}
        {characterRows.length > 0 ? (
          <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
            {characterRows.map((item) => (
              <li className="min-w-0" key={item.id}>
                <Button
                  aria-haspopup="dialog"
                  className="group grid min-h-[104px] w-full grid-cols-[56px_minmax(0,1fr)] gap-3 rounded-sm border border-border bg-surface p-3 text-left transition-colors hover:border-[var(--ui-border-strong)] hover:bg-muted"
                  type="button"
                  variant="unstyled"
                  onClick={() => {
                    setCharacter(item);
                  }}
                >
                  <img
                    alt=""
                    className="h-20 w-14 rounded-sm bg-muted object-cover object-top ring-1 ring-inset ring-border-subtle"
                    decoding="async"
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    src={item.image_thumbnail || coverPlaceholder}
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-foreground group-hover:text-[var(--ui-accent-text)]">
                      {item.name}
                    </span>
                    <span className="mt-1 block truncate text-xs text-muted-foreground">
                      {item.role || item.type || t('subject.character')}
                    </span>
                    <span className="mt-3 grid gap-1">
                      {(item.actors ?? []).slice(0, 2).map((actor) => (
                        <span className="grid grid-cols-[24px_minmax(0,1fr)] items-center gap-2" key={actor.id}>
                          <img
                            alt=""
                            className="size-6 rounded-full bg-muted object-cover object-top ring-1 ring-inset ring-border-subtle"
                            decoding="async"
                            loading="lazy"
                            referrerPolicy="no-referrer"
                            src={actor.image_thumbnail || coverPlaceholder}
                          />
                          <span className="truncate text-xs text-muted-foreground">{actor.name}</span>
                        </span>
                      ))}
                      {(item.actors ?? []).length === 0 ? (
                        <span className="text-xs text-subtle-foreground">{emptyText}</span>
                      ) : null}
                    </span>
                  </span>
                </Button>
              </li>
            ))}
          </ul>
        ) : null}
        {!query.isFetching && !query.isError && characterRows.length === 0 ? <EmptyState title={emptyText} /> : null}
        {characterRows.length > 0 ? (
          <Pagination currentPage={page} totalPages={totalPages} onPageChange={setPage} />
        ) : null}
      </DetailSection>

      <Dialog
        open={Boolean(character)}
        onOpenChange={(open) => {
          if (!open) setCharacter(null);
        }}
      >
        <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-2xl overflow-y-auto">
          {character ? (
            <>
              <DialogHeader>
                <DialogTitle>{character.name}</DialogTitle>
                <DialogDescription>
                  {[character.role, character.type].filter(Boolean).join(' · ') || t('subject.characterDetail')}
                </DialogDescription>
              </DialogHeader>
              <DetailShell
                image={character.image_original || character.image_thumbnail}
                title={character.name}
                subtitle={[character.role, character.type].filter(Boolean).join(' · ')}
                description={character.description}
                emptyLabel={emptyText}
                rows={[
                  ...detailRows([
                    [t('subject.gender'), character.gender],
                    [t('subject.birth'), character.birth],
                    [t('subject.bloodType'), character.blood_type],
                  ]),
                  ...getInfoboxRows(character.infobox)
                    .slice(0, 8)
                    .map((item) => [item.key, item.value] as const),
                ]}
              >
                {(character.actors ?? []).length ? (
                  <section className="grid gap-3">
                    <h4 className="text-sm font-semibold text-[var(--ui-text)]">{t('subject.voiceCast')}</h4>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {(character.actors ?? []).map((actor) => (
                        <Button
                          aria-haspopup="dialog"
                          className="grid grid-cols-[40px_minmax(0,1fr)] items-center gap-3 rounded-sm border border-border bg-surface p-2 text-left transition-colors hover:border-[var(--ui-border-strong)] hover:bg-muted"
                          key={actor.id}
                          type="button"
                          variant="unstyled"
                          onClick={() => {
                            setStaff(actor);
                          }}
                        >
                          <img
                            alt=""
                            className="size-10 rounded-sm bg-muted object-cover object-top ring-1 ring-inset ring-border-subtle"
                            decoding="async"
                            loading="lazy"
                            referrerPolicy="no-referrer"
                            src={actor.image_thumbnail || coverPlaceholder}
                          />
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-semibold text-foreground">{actor.name}</span>
                            <span className="block truncate text-xs text-muted-foreground">
                              {actor.type || t('subject.voice')}
                            </span>
                          </span>
                        </Button>
                      ))}
                    </div>
                  </section>
                ) : null}
              </DetailShell>
            </>
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(staff)}
        onOpenChange={(open) => {
          if (!open) setStaff(null);
        }}
      >
        <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-2xl overflow-y-auto">
          {staff ? (
            <>
              <DialogHeader>
                <DialogTitle>{staff.name}</DialogTitle>
                <DialogDescription>{staff.role || staff.type || t('subject.staffDetail')}</DialogDescription>
              </DialogHeader>
              <StaffDetail emptyLabel={emptyText} labels={staffLabels} staff={staff} />
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
