import { FormEvent, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, Star } from 'lucide-react';
import { CommunityContentCard } from '@/features/community/components/CommunityContentCard';
import { communityMutations, communityQueries, communityQueryKeys } from '@/features/community/community-queries';
import { useI18n } from '@/features/i18n/use-i18n';
import { routes } from '@/routes/paths';
import { Badge } from '@/shared/ui/Badge';
import { Button } from '@/shared/ui/Button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Page } from '@/shared/ui/Page';
import { Pagination } from '@/shared/ui/Pagination';

const pageSize = 16;

function formatDate(value?: string) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

export function CommunityPostsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentPage = Math.max(1, Number(searchParams.get('page') ?? '1') || 1);
  const [createOpen, setCreateOpen] = useState(false);
  const [content, setContent] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [visibility, setVisibility] = useState<'public' | 'followers' | 'private'>('public');
  const [isSpoiler, setIsSpoiler] = useState(false);
  const [isNsfw, setIsNsfw] = useState(false);
  const postsQuery = useQuery(communityQueries.posts({ page: currentPage, page_size: pageSize, ordering: '-last_activity_at' }));
  const createPostMutation = useMutation({
    ...communityMutations.createPost(),
    onSuccess: async () => {
      setCreateOpen(false);
      setContent('');
      setSubjectId('');
      setVisibility('public');
      setIsSpoiler(false);
      setIsNsfw(false);
      await queryClient.invalidateQueries({ queryKey: communityQueryKeys.posts() });
    },
  });
  const posts = postsQuery.data?.results ?? [];
  const totalPages = Math.max(1, Math.ceil((postsQuery.data?.count ?? 0) / pageSize));

  function goToPage(page: number) {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(page));
    setSearchParams(next);
  }

  function submitPost(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!content.trim()) return;
    createPostMutation.mutate({
      content,
      subject_id: subjectId.trim() || undefined,
      visibility,
      is_spoiler: isSpoiler,
      is_nsfw: isNsfw,
    });
  }

  return (
    <Page
      title={t('community.postsTitle')}
      eyebrow={t('nav.groupWorkspace')}
      description={t('community.postsDescription')}
      actions={(
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button type="button"><MessageSquare className="size-4" /> {t('community.newPost')}</Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{t('community.createPostTitle')}</DialogTitle>
              <DialogDescription>{t('community.createPostDescription')}</DialogDescription>
            </DialogHeader>
            <form className="grid gap-4" onSubmit={submitPost}>
              <textarea
                className="min-h-36 resize-y rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm leading-6 outline-none transition placeholder:text-neutral-400 focus:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-900"
                value={content}
                placeholder={t('community.postPlaceholder')}
                onChange={(event) => setContent(event.target.value)}
              />
              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px]">
                <label className="grid gap-1.5 text-sm">
                  <span className="font-semibold text-neutral-950 dark:text-white">{t('community.attachSubjectId')}</span>
                  <input
                    className="h-10 rounded-lg border border-neutral-200 bg-neutral-50 px-3 outline-none transition placeholder:text-neutral-400 focus:border-[var(--color-accent-border)] dark:border-neutral-800 dark:bg-neutral-900"
                    value={subjectId}
                    placeholder="00000000-0000-0000-0000-000000000000"
                    onChange={(event) => setSubjectId(event.target.value)}
                  />
                </label>
                <div className="grid gap-1.5 text-sm">
                  <span className="font-semibold text-neutral-950 dark:text-white">{t('community.visibility')}</span>
                  <div className="grid grid-cols-3 gap-1 rounded-lg border border-neutral-200 bg-neutral-50 p-1 dark:border-neutral-800 dark:bg-neutral-900">
                    {[
                      ['public', t('common.public')],
                      ['followers', t('community.followersVisibility')],
                      ['private', t('common.private')],
                    ].map(([value, label]) => (
                      <button
                        className={[
                          'h-8 rounded-md px-2 text-xs font-semibold transition',
                          visibility === value
                            ? 'bg-white text-neutral-950 shadow-sm dark:bg-neutral-950 dark:text-white'
                            : 'text-neutral-500 hover:text-neutral-950 dark:text-neutral-400 dark:hover:text-white',
                        ].join(' ')}
                        key={value}
                        type="button"
                        onClick={() => setVisibility(value as 'public' | 'followers' | 'private')}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-3 text-sm text-neutral-500 dark:text-neutral-400">
                <label className="inline-flex items-center gap-2">
                  <input checked={isSpoiler} className="size-4 accent-[var(--color-accent)]" type="checkbox" onChange={(event) => setIsSpoiler(event.target.checked)} />
                  {t('community.markSpoiler')}
                </label>
                <label className="inline-flex items-center gap-2">
                  <input checked={isNsfw} className="size-4 accent-[var(--color-accent)]" type="checkbox" onChange={(event) => setIsNsfw(event.target.checked)} />
                  NSFW
                </label>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>{t('common.cancel')}</Button>
                <Button disabled={createPostMutation.isPending || !content.trim()} type="submit">
                  <MessageSquare className="size-4" /> {t('community.publishPost')}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      )}
    >
      {postsQuery.isLoading ? <LoadingState title={t('community.loadingPosts')} /> : null}
      {postsQuery.isError ? <ErrorState title={t('community.postsErrorTitle')} description={t('community.postsErrorBody')} /> : null}
      {!postsQuery.isLoading && !postsQuery.isError && posts.length === 0 ? (
        <EmptyState title={t('community.noPostsTitle')} description={t('community.noPostsBody')} />
      ) : null}
      <div className="grid gap-3">
        {posts.map((post) => (
          <CommunityContentCard
            actions={(
              <Button asChild size="sm" type="button" variant="secondary">
                <Link to={routes.communityPost(post.id)}>{t('community.viewPost')}</Link>
              </Button>
            )}
            author={post.author?.id ? {
              href: routes.userProfile(post.author.id),
              name: post.author.nickname || t('common.anonymous'),
              avatar: post.author.avatar,
            } : undefined}
            badges={(
              <>
                <Badge variant="secondary"><Star className="size-3" /> {post.reaction_count ?? 0}</Badge>
                <Badge variant="secondary"><MessageSquare className="size-3" /> {post.reply_count ?? 0}</Badge>
                {post.is_nsfw ? <Badge>NSFW</Badge> : null}
                {post.is_spoiler ? <Badge>{t('common.spoiler')}</Badge> : null}
              </>
            )}
            body={post.content}
            cover={post.subject?.image_thumbnail || null}
            date={formatDate(post.last_activity_at || post.created_at)}
            href={routes.communityPost(post.id)}
            icon={<MessageSquare className="size-4" />}
            isSpoiler={post.is_spoiler}
            key={post.id}
            subject={post.subject ? {
              href: routes.subject(post.subject.id),
              title: post.subject.title || post.subject.title_cn || t('common.untitledSubject'),
            } : undefined}
            title={post.content.split('\n').find(Boolean)?.slice(0, 96) || t('community.postDetailTitle')}
            typeLabel={t('community.targetType.post')}
          />
        ))}
      </div>
      <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={goToPage} />
    </Page>
  );
}
