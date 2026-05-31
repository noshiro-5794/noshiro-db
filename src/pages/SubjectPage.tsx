import { type FormEvent, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/features/auth/use-auth';
import { libraryMutations, libraryQueries, libraryQueryKeys } from '@/features/library/library-queries';
import { subjectQueries } from '@/features/subjects/subject-queries';
import type { SubjectDetail, SubjectEpisode, UserSubjectStatus } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { Button } from '@/shared/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/Card';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { FilterMenu } from '@/shared/ui/FilterMenu';
import { Input } from '@/shared/ui/Input';
import { Page } from '@/shared/ui/Page';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';

const statusOptions: Array<{ label: string; value: UserSubjectStatus }> = [
  { label: 'Wish', value: 'wish' },
  { label: 'Watching', value: 'doing' },
  { label: 'Completed', value: 'done' },
  { label: 'On hold', value: 'on_hold' },
  { label: 'Dropped', value: 'drop' },
];

const simpleRatingOptions: Array<{ label: string; value: string }> = [
  { label: 'No simple rating', value: '' },
  { label: '1', value: '1' },
  { label: '2', value: '2' },
  { label: '3', value: '3' },
  { label: '4', value: '4' },
  { label: '5', value: '5' },
];

function titleOf(subject: SubjectDetail) {
  return subject.display_title || subject.title || subject.title_cn || 'Untitled';
}

function metaOf(subject: SubjectDetail) {
  return [subject.subject_type, subject.platform, subject.date].filter(Boolean).join(' · ');
}

function episodeTitle(episode: SubjectEpisode) {
  return episode.title || (episode.ep_num ? `Episode ${episode.ep_num}` : `Episode ${episode.id}`);
}

export function SubjectPage() {
  const { subjectId } = useParams();
  const auth = useAuth();
  const isAuthenticated = auth.isAuthenticated;
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<UserSubjectStatus>('wish');
  const [simpleRating, setSimpleRating] = useState('');
  const [rating, setRating] = useState('');
  const [comment, setComment] = useState('');
  const [isPublic, setIsPublic] = useState(true);
  const [noticeMessage, setNoticeMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const detailQuery = useQuery({
    ...subjectQueries.detail(subjectId ?? ''),
    enabled: Boolean(subjectId),
  });
  const episodesQuery = useQuery({
    ...subjectQueries.episodes(subjectId ?? ''),
    enabled: Boolean(subjectId),
  });
  const relationsQuery = useQuery({
    ...subjectQueries.relations(subjectId ?? ''),
    enabled: Boolean(subjectId),
  });
  const contextQuery = useQuery({
    ...libraryQueries.subjectContext(subjectId ?? ''),
    enabled: Boolean(subjectId) && isAuthenticated,
  });
  const progressQuery = useQuery({
    ...libraryQueries.progress(subjectId ?? ''),
    enabled: Boolean(subjectId) && isAuthenticated,
  });

  const createSubjectMutation = useMutation(libraryMutations.createUserSubject());
  const updateSubjectMutation = useMutation(libraryMutations.updateUserSubject());
  const deleteSubjectMutation = useMutation(libraryMutations.deleteUserSubject());
  const setEpisodeFinishedMutation = useMutation(libraryMutations.setEpisodeFinished());

  const userSubject = contextQuery.data?.user_subject ?? null;
  const progress = progressQuery.data;

  useEffect(() => {
    if (!userSubject) {
      setStatus('wish');
      setSimpleRating('');
      setRating('');
      setComment('');
      setIsPublic(true);
      return;
    }

    setStatus(userSubject.status as UserSubjectStatus);
    setSimpleRating(userSubject.simple_rating ? String(userSubject.simple_rating) : '');
    setRating(userSubject.rating ? String(userSubject.rating) : '');
    setComment(userSubject.comment ?? '');
    setIsPublic(userSubject.is_public);
  }, [userSubject]);

  async function refreshUserSubjectData() {
    if (!subjectId) return;
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.subjectContext(subjectId) }),
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.progress(subjectId) }),
      queryClient.invalidateQueries({ queryKey: libraryQueryKeys.userSubjects() }),
    ]);
  }

  async function handleMarkSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!subjectId) return;

    setNoticeMessage('');
    setErrorMessage('');
    const body = {
      status,
      simple_rating: simpleRating ? Number(simpleRating) : undefined,
      rating: rating.trim() || undefined,
      comment,
      is_public: isPublic,
    };

    try {
      if (userSubject) {
        await updateSubjectMutation.mutateAsync({
          userSubjectId: userSubject.id,
          body,
        });
        setNoticeMessage('Subject mark updated.');
      } else {
        await createSubjectMutation.mutateAsync({
          subject_id: subjectId,
          ...body,
        });
        setNoticeMessage('Subject marked.');
      }
      await refreshUserSubjectData();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Request failed');
    }
  }

  async function handleDeleteMark() {
    if (!userSubject) return;
    setNoticeMessage('');
    setErrorMessage('');
    try {
      await deleteSubjectMutation.mutateAsync(userSubject.id);
      setNoticeMessage('Subject mark deleted.');
      await refreshUserSubjectData();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Request failed');
    }
  }

  async function handleEpisodeToggle(episodeId: number, isFinished: boolean) {
    if (!subjectId) return;
    await setEpisodeFinishedMutation.mutateAsync({ subjectId, episodeId, isFinished });
    await queryClient.invalidateQueries({ queryKey: libraryQueryKeys.progress(subjectId) });
  }

  if (!subjectId) {
    return (
      <Page title="Subject detail">
        <EmptyState title="Missing subject ID." description="Open a subject from search results." />
      </Page>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <Page title="Subject detail" description="Loading subject data from the backend.">
        <LoadingState title="Loading subject" description="Fetching detail, episodes, and relation modules." />
      </Page>
    );
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <Page title="Subject detail">
        <ErrorState title="Unable to load this subject." description="Check the backend connection or try another subject." />
      </Page>
    );
  }

  const subject = detailQuery.data;
  const relationItems = [...(relationsQuery.data?.outgoing ?? []), ...(relationsQuery.data?.incoming ?? [])];
  const episodeProgressIds = new Set(progress?.finished_episode_ids ?? []);
  const totalEpisodes = progress?.total_episodes || subject.episode_count || episodesQuery.data?.count || 0;
  const finishedCount = progress?.finished_count ?? 0;

  return (
    <Page title={titleOf(subject)} eyebrow="Subject detail" description={metaOf(subject)}>
      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="grid content-start gap-4">
          <img
            className="aspect-[2/3] w-full rounded-2xl bg-neutral-100 object-cover shadow-sm ring-1 ring-neutral-200 dark:bg-neutral-900 dark:ring-neutral-800"
            src={subject.image || subject.image_thumbnail || coverPlaceholder}
            alt=""
          />

          <Card>
            <CardHeader>
              <CardTitle>My mark</CardTitle>
              <CardDescription>{isAuthenticated ? 'Manage your personal status for this subject.' : 'Log in to mark this subject.'}</CardDescription>
            </CardHeader>
            <CardContent>
              {!isAuthenticated ? (
                <Button asChild className="w-full">
                  <Link to={routes.login}>Log in</Link>
                </Button>
              ) : (
                <form className="grid gap-3" onSubmit={handleMarkSubmit}>
                  <FilterMenu label="Status" options={statusOptions} value={status} onChange={setStatus} />
                  <FilterMenu label="Simple" options={simpleRatingOptions} value={simpleRating} onChange={setSimpleRating} />
                  <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                    Rating
                    <Input inputMode="decimal" placeholder="0.0 - 10.0" value={rating} onChange={(event) => setRating(event.target.value)} />
                  </label>
                  <label className="grid gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
                    Comment
                    <textarea
                      className="min-h-24 rounded-xl border-0 bg-white px-3 py-2 text-sm shadow-sm outline-none ring-1 ring-neutral-200 focus:ring-4 focus:ring-neutral-200 dark:bg-neutral-950 dark:ring-neutral-800 dark:focus:ring-neutral-800"
                      value={comment}
                      onChange={(event) => setComment(event.target.value)}
                    />
                  </label>
                  <label className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
                    <input checked={isPublic} type="checkbox" onChange={(event) => setIsPublic(event.target.checked)} />
                    Public
                  </label>
                  {noticeMessage ? <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">{noticeMessage}</p> : null}
                  {errorMessage ? <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-300">{errorMessage}</p> : null}
                  <Button disabled={createSubjectMutation.isPending || updateSubjectMutation.isPending} type="submit">
                    {userSubject ? 'Save mark' : 'Mark subject'}
                  </Button>
                  {userSubject ? (
                    <Button disabled={deleteSubjectMutation.isPending} type="button" variant="secondary" onClick={handleDeleteMark}>
                      Delete mark
                    </Button>
                  ) : null}
                </form>
              )}
            </CardContent>
          </Card>
        </aside>

        <main className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Overview</CardTitle>
              <CardDescription>{subject.title}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <p className="text-sm leading-7 text-neutral-600 dark:text-neutral-300">
                {subject.summary || 'No summary has been provided by the backend yet.'}
              </p>
              {subject.tags?.length ? (
                <div className="flex flex-wrap gap-2">
                  {subject.tags.slice(0, 12).map((tag) => (
                    <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400" key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardContent className="p-5">
                <strong className="text-2xl text-neutral-950 dark:text-white">{subject.episode_count}</strong>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">Episodes</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <strong className="text-2xl text-neutral-950 dark:text-white">{subject.staff_count}</strong>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">Staff</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <strong className="text-2xl text-neutral-950 dark:text-white">{subject.character_count}</strong>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">Characters</p>
              </CardContent>
            </Card>
          </div>

          {isAuthenticated ? (
            <Card>
              <CardHeader>
                <CardTitle>Progress</CardTitle>
                <CardDescription>
                  {finishedCount} / {totalEpisodes} episodes finished
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2">
                  {(progress?.episodes ?? episodesQuery.data?.results ?? []).slice(0, 48).map((episode) => {
                    const checked = 'is_finished' in episode ? episode.is_finished : episodeProgressIds.has(episode.id);
                    return (
                      <button
                        className={`grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm transition ${
                          checked
                            ? 'border-[var(--color-accent-border)] bg-[var(--color-accent-soft)]'
                            : 'border-neutral-200 bg-white hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-950'
                        }`}
                        key={episode.id}
                        type="button"
                        onClick={() => handleEpisodeToggle(episode.id, !checked)}
                      >
                        <span className="size-2 rounded-full bg-[var(--color-accent)] opacity-70" />
                        <span className="min-w-0 truncate">{episodeTitle(episode)}</span>
                        <span className="text-xs text-neutral-400">{checked ? 'Done' : 'Todo'}</span>
                      </button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Relations</CardTitle>
              <CardDescription>{relationsQuery.isFetching ? 'Loading relations' : `${relationItems.length} related subjects`}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2">
                {relationItems.slice(0, 8).map((relation) => (
                  <Link className="flex items-center justify-between gap-4 rounded-lg border border-neutral-200 px-3 py-2 text-sm transition hover:border-[var(--color-accent-border)] dark:border-neutral-800" key={`${relation.relation}-${relation.subject.id}`} to={routes.subject(relation.subject.id)}>
                    <span className="min-w-0 truncate font-medium text-neutral-950 dark:text-white">{relation.subject.display_title || relation.subject.title}</span>
                    <span className="text-neutral-500 dark:text-neutral-400">{relation.relation}</span>
                  </Link>
                ))}
                {!relationsQuery.isFetching && relationItems.length === 0 ? <p className="text-sm text-neutral-500 dark:text-neutral-400">No relations returned yet.</p> : null}
              </div>
            </CardContent>
          </Card>

          {isAuthenticated ? (
            <Card>
              <CardHeader>
                <CardTitle>Reviews</CardTitle>
                <CardDescription>Markdown reviews you created for this subject.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3">
                  {(contextQuery.data?.reviews ?? []).map((review) => (
                    <article className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800" key={review.id}>
                      <h3 className="font-semibold text-neutral-950 dark:text-white">{review.title}</h3>
                      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                        {review.is_public ? 'Public' : 'Private'}
                        {review.is_spoiler ? ' · Spoiler' : ''}
                      </p>
                    </article>
                  ))}
                  {!contextQuery.isFetching && (contextQuery.data?.reviews ?? []).length === 0 ? (
                    <p className="text-sm text-neutral-500 dark:text-neutral-400">No reviews have been created for this subject yet.</p>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ) : null}
        </main>
      </div>
    </Page>
  );
}
