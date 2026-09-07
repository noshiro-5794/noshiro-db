import { useId, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check } from 'lucide-react';
import { libraryMutations, libraryQueryKeys } from '@/entities/library';
import { useAuth } from '@/entities/session';
import { subjectQueries } from '@/entities/subject';
import type { ProgressSummary, SubjectDetail } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { cn } from '@/shared/lib/cn';
import { Button } from '@/shared/ui/Button';
import { DetailSection } from '@/shared/ui/Detail';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Pagination } from '@/shared/ui/Pagination';
import { toast } from '@/shared/ui/toast';
import { episodeLabel, episodeMeta, episodeTitle, posterOf } from '../model/subject-detail';
import { DetailShell } from './SubjectDetailPrimitives';

const episodePageSize = 12;
const otherEpisodePageSize = 8;

export function EpisodesSection({
  className,
  progress,
  subject,
  userSubjectExists,
}: {
  className?: string;
  progress: ProgressSummary | undefined;
  subject: SubjectDetail;
  userSubjectExists: boolean;
}) {
  const { t } = useI18n();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const emptyText = t('common.none');
  const sectionTitleId = useId();
  const otherChaptersTitleId = useId();
  const [episodePage, setEpisodePage] = useState(1);
  const [otherEpisodePage, setOtherEpisodePage] = useState(1);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string | null>(null);
  const [pendingEpisodeId, setPendingEpisodeId] = useState<string | null>(null);
  const episodeMutationInFlight = useRef(false);
  const episodesQuery = useQuery(
    subjectQueries.episodes(subject.id, { page: episodePage, page_size: episodePageSize, type: 'EP' }),
  );
  const otherEpisodesQuery = useQuery(subjectQueries.allEpisodes(subject.id));
  const selectedEpisodeQuery = useQuery({
    ...subjectQueries.episode(subject.id, selectedEpisodeId ?? ''),
    enabled: selectedEpisodeId !== null,
  });
  const setEpisodeFinishedMutation = useMutation(libraryMutations.setEpisodeFinished());
  const episodeRows = episodesQuery.data?.results ?? progress?.episodes ?? [];
  const finishedEpisodeIds = new Set(progress?.finished_episode_ids ?? []);
  const allOtherEpisodes = (otherEpisodesQuery.data ?? []).filter((episode) => episode.type !== 'EP');
  const otherEpisodeRows = allOtherEpisodes.slice(
    (otherEpisodePage - 1) * otherEpisodePageSize,
    otherEpisodePage * otherEpisodePageSize,
  );
  const episodeTotalPages = Math.max(1, Math.ceil((episodesQuery.data?.count ?? 0) / episodePageSize));
  const otherEpisodeTotalPages = Math.max(1, Math.ceil(allOtherEpisodes.length / otherEpisodePageSize));
  const selectedEpisodePreview = [...episodeRows, ...allOtherEpisodes].find(
    (episode) => episode.id === selectedEpisodeId,
  );
  const selectedEpisode = selectedEpisodeQuery.data ?? selectedEpisodePreview;

  async function handleEpisodeToggle(episodeId: string, isFinished: boolean) {
    if (episodeMutationInFlight.current) return;
    episodeMutationInFlight.current = true;
    setPendingEpisodeId(episodeId);
    try {
      const nextProgress = await setEpisodeFinishedMutation.mutateAsync({
        subjectId: subject.id,
        episodeId,
        isFinished,
      });
      queryClient.setQueryData<ProgressSummary>(libraryQueryKeys.progress(subject.id), nextProgress);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.subjectContext(subject.id) }),
        queryClient.invalidateQueries({ queryKey: libraryQueryKeys.progress(subject.id) }),
      ]);
    } catch (error) {
      toast.error(t('common.requestFailed'), error instanceof Error ? error.message : undefined);
    } finally {
      episodeMutationInFlight.current = false;
      setPendingEpisodeId(null);
    }
  }

  function handleProgressClick(episodeId: string, isFinished: boolean) {
    if (!isAuthenticated) {
      toast.info(t('subject.loginToTrackProgress'));
      return;
    }
    if (!userSubjectExists) {
      toast.info(t('subject.markBeforeProgress'));
      return;
    }
    void handleEpisodeToggle(episodeId, isFinished);
  }

  return (
    <>
      <DetailSection
        className={className}
        id="episodes"
        meta={
          episodesQuery.isLoading && episodeRows.length === 0
            ? undefined
            : `${episodesQuery.data?.count ?? episodeRows.length} ${t('common.items')}`
        }
        title={t('subject.episodes')}
        titleId={sectionTitleId}
      >
        {episodesQuery.isLoading && episodeRows.length === 0 ? (
          <LoadingState title={t('subject.loadingEpisode')} />
        ) : null}
        {episodesQuery.isError ? (
          <ErrorState
            action={
              <Button size="sm" variant="secondary" onClick={() => void episodesQuery.refetch()}>
                {t('common.retry')}
              </Button>
            }
            description={t('common.requestFailed')}
            title={t('subject.episodeErrorTitle')}
          />
        ) : null}
        {episodeRows.length > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {episodeRows.map((episode) => {
              const checked = finishedEpisodeIds.has(episode.id);
              const isPending = pendingEpisodeId === episode.id;
              const progressLabel = isPending
                ? t('common.saving')
                : checked
                  ? t('subject.watched')
                  : t('subject.markWatched');
              return (
                <article
                  className={cn(
                    'grid min-h-24 grid-rows-[auto_1fr] gap-2 rounded-sm border border-border bg-surface px-3 py-3 transition-colors hover:border-[var(--ui-border-strong)]',
                    checked &&
                      'border-[color-mix(in_srgb,var(--ui-accent)_24%,var(--ui-border))] bg-[color-mix(in_srgb,var(--ui-accent-soft)_52%,var(--ui-bg-surface))]',
                  )}
                  key={episode.id}
                >
                  <span className="flex min-w-0 items-center justify-between gap-2">
                    <span className="min-w-0 truncate text-xs font-semibold uppercase text-muted-foreground">
                      {episodeLabel(episode)}
                    </span>
                    <Button
                      aria-busy={isPending || undefined}
                      aria-label={`${episodeLabel(episode)}: ${progressLabel}`}
                      aria-pressed={checked}
                      className={cn(
                        'inline-flex shrink-0 items-center gap-1 rounded-sm px-1.5 py-1 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                        checked && 'bg-[var(--ui-accent-soft)] text-[var(--ui-accent-text)]',
                      )}
                      disabled={pendingEpisodeId !== null}
                      type="button"
                      variant="unstyled"
                      onClick={() => {
                        handleProgressClick(episode.id, !checked);
                      }}
                    >
                      {checked ? <Check aria-hidden="true" className="size-3" /> : null}
                      {progressLabel}
                    </Button>
                  </span>
                  <Button
                    aria-haspopup="dialog"
                    className="group grid min-h-0 grid-rows-[1fr_auto] gap-2 rounded-sm text-left"
                    type="button"
                    variant="unstyled"
                    onClick={() => {
                      setSelectedEpisodeId(episode.id);
                    }}
                  >
                    <span className="line-clamp-2 text-sm font-semibold leading-5 text-foreground group-hover:text-[var(--ui-accent-text)]">
                      {episodeTitle(episode)}
                    </span>
                    <span className="flex min-w-0 items-center justify-between gap-2 text-xs text-muted-foreground">
                      <span className="truncate">{episodeMeta(episode, emptyText)}</span>
                      <span className="font-semibold text-[var(--ui-accent-text)]">{episode.type}</span>
                    </span>
                  </Button>
                </article>
              );
            })}
          </div>
        ) : null}
        {!episodesQuery.isFetching && !episodesQuery.isError && episodeRows.length === 0 ? (
          <EmptyState title={emptyText} />
        ) : null}
        {episodeRows.length > 0 ? (
          <Pagination currentPage={episodePage} totalPages={episodeTotalPages} onPageChange={setEpisodePage} />
        ) : null}

        {otherEpisodesQuery.isLoading || otherEpisodesQuery.isError || otherEpisodeRows.length > 0 ? (
          <section aria-labelledby={otherChaptersTitleId} className="grid gap-3 border-t border-border-subtle pt-4">
            <h3 className="m-0 text-sm font-semibold text-foreground" id={otherChaptersTitleId}>
              {t('subject.otherChapters')}
            </h3>
            {otherEpisodesQuery.isLoading ? <LoadingState title={t('subject.otherChapters')} /> : null}
            {otherEpisodesQuery.isError ? (
              <ErrorState
                action={
                  <Button size="sm" variant="secondary" onClick={() => void otherEpisodesQuery.refetch()}>
                    {t('common.retry')}
                  </Button>
                }
                description={t('common.requestFailed')}
                title={t('subject.otherChapters')}
              />
            ) : null}
            {otherEpisodeRows.length > 0 ? (
              <div className="grid gap-2 sm:grid-cols-2">
                {otherEpisodeRows.map((episode) => (
                  <Button
                    aria-haspopup="dialog"
                    className="group grid min-h-[68px] grid-cols-[3.5rem_minmax(0,1fr)] items-center gap-3 rounded-sm border border-border bg-surface p-3 text-left text-sm transition-colors hover:border-[var(--ui-border-strong)] hover:bg-muted"
                    key={episode.id}
                    type="button"
                    variant="unstyled"
                    onClick={() => {
                      setSelectedEpisodeId(episode.id);
                    }}
                  >
                    <span className="rounded-sm bg-muted px-2 py-1 text-center text-xs font-semibold uppercase text-muted-foreground">
                      {episode.type}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate font-semibold text-foreground group-hover:text-[var(--ui-accent-text)]">
                        {episodeTitle(episode)}
                      </span>
                      <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                        {episodeLabel(episode)} · {episodeMeta(episode, emptyText)}
                      </span>
                    </span>
                  </Button>
                ))}
              </div>
            ) : null}
            {otherEpisodeRows.length > 0 ? (
              <Pagination
                currentPage={otherEpisodePage}
                totalPages={otherEpisodeTotalPages}
                onPageChange={setOtherEpisodePage}
              />
            ) : null}
          </section>
        ) : null}
      </DetailSection>

      <Dialog
        open={selectedEpisodeId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedEpisodeId(null);
        }}
      >
        <DialogContent className="max-w-lg">
          {selectedEpisodeQuery.isLoading && !selectedEpisodePreview ? (
            <LoadingState title={t('subject.loadingEpisode')} />
          ) : selectedEpisodeQuery.isError ? (
            <ErrorState title={t('subject.episodeErrorTitle')} />
          ) : selectedEpisode ? (
            <>
              <DialogHeader>
                <DialogTitle>{episodeTitle(selectedEpisode)}</DialogTitle>
                <DialogDescription>
                  {[episodeLabel(selectedEpisode), selectedEpisode.type, selectedEpisode.date]
                    .filter(Boolean)
                    .join(' · ') || t('subject.episodeDetail')}
                </DialogDescription>
              </DialogHeader>
              <DetailShell
                image={posterOf(subject)}
                title={episodeTitle(selectedEpisode)}
                subtitle={episodeLabel(selectedEpisode)}
                description={selectedEpisode.description}
                emptyLabel={emptyText}
                rows={[
                  [t('subject.type'), selectedEpisode.type],
                  [t('subject.episode'), selectedEpisode.ep_num === null ? '' : String(selectedEpisode.ep_num)],
                  [t('subject.sort'), selectedEpisode.sort === null ? '' : selectedEpisode.sort],
                  [t('subject.date'), selectedEpisode.date ?? ''],
                  [t('subject.duration'), selectedEpisode.duration ?? ''],
                ].filter((row): row is [string, string] => Boolean(row[1]))}
              />
            </>
          ) : (
            <EmptyState title={emptyText} />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
