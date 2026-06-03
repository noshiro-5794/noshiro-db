import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { Badge } from '@/shared/ui/Badge';

type CommunityContentCardProps = {
  href: string;
  title: string;
  body?: string;
  date?: string;
  cover?: string | null;
  icon?: ReactNode;
  typeLabel?: string;
  subject?: {
    href: string;
    title: string;
    cover?: string | null;
  };
  author?: {
    href: string;
    name: string;
    avatar?: string | null;
  };
  badges?: ReactNode;
  actions?: ReactNode;
  isSpoiler?: boolean;
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
}: CommunityContentCardProps) {
  return (
    <article className="community-content-card">
      <Link className="community-content-media" to={subject?.href || href}>
        {cover ? <img src={cover} alt="" /> : <span>{icon}</span>}
      </Link>
      <div className="community-content-main">
        <div className="community-content-meta">
          {typeLabel ? <Badge variant="secondary">{typeLabel}</Badge> : null}
          {subject ? <Link to={subject.href}>{subject.title}</Link> : null}
          {date ? <span>{date}</span> : null}
          {badges}
        </div>
        <Link className="community-content-title" to={href}>
          {title}
        </Link>
        {body ? <p className={`community-content-body ${isSpoiler ? 'is-spoiler' : ''}`}>{body}</p> : null}
        <div className="community-content-footer">
          <div className="community-content-author">
            {author ? (
              <Link to={author.href}>
                <img src={author.avatar || '/assets/placeholders/avatar.png'} alt="" />
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
