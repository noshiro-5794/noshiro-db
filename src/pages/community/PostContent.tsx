import { placeholderImagePaths } from '@/shared/assets/public-assets';
import { formatDateTime as formatDate } from '@/shared/lib/date';
import { ShieldAlert } from 'lucide-react';
import { Link } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import type { CommunityPostSummary } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Avatar } from '@/shared/ui/Avatar';
import { Badge } from '@/shared/ui/Badge';
import { DetailBody, DetailHeader } from '@/shared/ui/Detail';
import { SensitiveContent } from '@/shared/ui/SensitiveContent';

function subjectTitle(post: CommunityPostSummary, fallback: string) {
  return post.subject?.title || post.subject?.title_cn || fallback;
}

function PostSubjectCard({ post }: { post: CommunityPostSummary }) {
  const { t } = useI18n();
  if (!post.subject) return null;

  return (
    <Link
      className="mt-5 grid grid-cols-[56px_minmax(0,1fr)] gap-3 rounded-sm border border-border bg-muted p-3 transition-colors hover:border-[var(--ui-accent-border)]"
      to={routes.subject(post.subject.id)}
    >
      <img
        className="h-20 w-14 rounded-sm bg-muted object-cover"
        src={post.subject.image_thumbnail || placeholderImagePaths.subjectCover}
        alt=""
        decoding="async"
        loading="lazy"
        referrerPolicy="no-referrer"
      />
      <span className="min-w-0 self-center">
        <span className="block truncate text-sm font-semibold text-foreground">
          {subjectTitle(post, t('common.untitledSubject'))}
        </span>
        <span className="mt-1 block text-xs text-muted-foreground">{post.subject.subject_type}</span>
        {post.subject.nsfw ? (
          <Badge className="mt-2" variant="warning">
            NSFW
          </Badge>
        ) : null}
      </span>
    </Link>
  );
}

export function PostContent({ post, title, titleId }: { post: CommunityPostSummary; title: string; titleId: string }) {
  const { t } = useI18n();
  const postDate = post.updated_at || post.created_at;

  return (
    <>
      <DetailHeader
        badges={
          <>
            {post.is_pinned ? <Badge variant="accent">{t('community.pinned')}</Badge> : null}
            {post.is_locked ? <Badge variant="secondary">{t('community.locked')}</Badge> : null}
            {post.is_nsfw ? <Badge variant="warning">NSFW</Badge> : null}
            {post.is_spoiler ? (
              <Badge variant="warning">
                <ShieldAlert className="size-3" /> {t('common.spoiler')}
              </Badge>
            ) : null}
          </>
        }
        meta={
          <>
            {post.author?.id ? (
              <Link to={routes.userProfile(post.author.id)}>
                <Avatar alt={post.author.nickname || t('common.anonymous')} src={post.author.avatar} />
              </Link>
            ) : (
              <Avatar />
            )}
            <div className="min-w-0">
              {post.author?.id ? (
                <Link
                  className="block truncate text-sm font-semibold text-foreground transition-colors hover:text-[var(--ui-accent-text)]"
                  to={routes.userProfile(post.author.id)}
                >
                  {post.author.nickname || t('common.anonymous')}
                </Link>
              ) : (
                <p className="truncate text-sm font-semibold text-foreground">{t('common.anonymous')}</p>
              )}
              <time className="block text-xs text-muted-foreground" dateTime={postDate}>
                {formatDate(postDate)}
              </time>
            </div>
          </>
        }
        title={title}
        titleId={titleId}
      />
      <SensitiveContent
        contentLabel={t('common.spoiler')}
        isSensitive={post.is_spoiler}
        revealLabel={t('common.revealSpoiler')}
      >
        <DetailBody>
          <p className="whitespace-pre-wrap text-[15px] leading-7 text-foreground">{post.content}</p>
          <PostSubjectCard post={post} />
        </DetailBody>
      </SensitiveContent>
    </>
  );
}
