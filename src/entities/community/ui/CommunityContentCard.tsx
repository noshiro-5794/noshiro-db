import { Link } from '@tanstack/react-router';
import type { ReactNode } from 'react';
import { Avatar } from '@/shared/ui/Avatar';
import { Badge } from '@/shared/ui/Badge';
import { useI18n } from '@/shared/i18n';
import { SpoilerText } from '@/shared/ui/SpoilerText';
import './community-content-card.css';

type CommunityContentCardProps = {
  href: string;
  title: string;
  body?: string;
  date?: string;
  cover?: string | null;
  icon?: ReactNode;
  typeLabel?: string;
  subject?:
    | {
        href: string;
        title: string;
        cover?: string | null;
      }
    | undefined;
  author?:
    | {
        href: string;
        name: string;
        avatar?: string | null;
      }
    | undefined;
  badges?: ReactNode;
  actions?: ReactNode;
  isSpoiler?: boolean;
  presentation?: 'card' | 'flat';
};

export function CommunityContentCard({
  href,
  title,
  body,
  date,
  cover,
  icon,
  typeLabel,
  subject,
  author,
  badges,
  actions,
  isSpoiler,
  presentation = 'card',
}: CommunityContentCardProps) {
  const { t } = useI18n();

  return (
    <article className={`community-content-card ${presentation === 'flat' ? 'is-flat' : ''}`}>
      <Link aria-label={subject?.title || title} className="community-content-media" to={subject?.href || href}>
        {cover ? (
          <img alt="" decoding="async" loading="lazy" referrerPolicy="no-referrer" src={cover} />
        ) : (
          <span>{icon}</span>
        )}
      </Link>
      <div className="community-content-main">
        <div className="community-content-meta">
          {typeLabel ? <Badge variant="secondary">{typeLabel}</Badge> : null}
          {subject ? <Link to={subject.href}>{subject.title}</Link> : null}
          {date ? <span>{date}</span> : null}
          {badges}
        </div>
        <h3 className="community-content-title">
          <Link to={href}>{title}</Link>
        </h3>
        {body ? (
          <SpoilerText
            className="community-content-body"
            isSpoiler={Boolean(isSpoiler)}
            revealLabel={t('common.revealSpoiler')}
          >
            {body}
          </SpoilerText>
        ) : null}
        <div className="community-content-footer">
          <div className="community-content-author">
            {author ? (
              <Link to={author.href}>
                <Avatar className="size-6" src={author.avatar} />
                <span>{author.name}</span>
              </Link>
            ) : null}
          </div>
          {actions ? <div className="community-content-actions">{actions}</div> : null}
        </div>
      </div>
    </article>
  );
}
