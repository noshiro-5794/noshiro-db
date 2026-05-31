import { Link } from 'react-router-dom';
import type { SubjectSummary } from '@/lib/api/types';
import { routes } from '@/routes/paths';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';

function getSubjectTitle(subject: SubjectSummary) {
  return subject.display_title || subject.title || subject.title_cn || 'Untitled';
}

function getSubjectPoster(subject: SubjectSummary) {
  return subject.images?.poster || subject.images?.thumbnail || subject.image_thumbnail || subject.image || coverPlaceholder;
}

function getSubjectMeta(subject: SubjectSummary) {
  return subject.display_subtitle || subject.display_meta?.join(' / ') || [
    subject.content?.episodes ? `${subject.content.episodes}话` : null,
    subject.year ? `${subject.year}` : subject.date,
    subject.platform,
  ].filter(Boolean).join(' / ');
}

type SubjectCardProps = {
  subject: SubjectSummary;
};

export function SubjectCard({ subject }: SubjectCardProps) {
  return (
    <Link className="subject-card" to={routes.subject(subject.id)}>
      <img
        className="subject-card-cover"
        src={getSubjectPoster(subject)}
        alt=""
        loading="lazy"
      />
      <span className="subject-card-body">
        <span className="subject-card-title">{getSubjectTitle(subject)}</span>
        <span className="subject-card-meta">{getSubjectMeta(subject) || subject.subject_type}</span>
      </span>
    </Link>
  );
}
