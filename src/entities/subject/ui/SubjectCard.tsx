import { Link, useLocation } from '@/shared/routing/navigation';
import { useI18n } from '@/shared/i18n';
import type { SubjectSummary } from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { routeBackState } from '@/shared/routing/route-state';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';
function getSubjectTitle(subject: SubjectSummary, fallback: string) {
  return subject.display_title || subject.title || subject.title_cn || fallback;
}

function getSubjectPoster(subject: SubjectSummary) {
  return (
    subject.images?.poster || subject.images?.thumbnail || subject.image_thumbnail || subject.image || coverPlaceholder
  );
}

function getSubjectMeta(subject: SubjectSummary, episodeUnit: string) {
  return (
    subject.display_subtitle ||
    subject.display_meta?.join(' / ') ||
    [
      subject.content?.episodes ? `${subject.content.episodes} ${episodeUnit}` : null,
      subject.year ? `${subject.year}` : subject.date,
      subject.platform,
    ]
      .filter(Boolean)
      .join(' / ')
  );
}

type SubjectCardProps = {
  subject: SubjectSummary;
};

export function SubjectCard({ subject }: SubjectCardProps) {
  const { t } = useI18n();
  const location = useLocation();

  return (
    <Link className="subject-card" state={routeBackState(location, t('nav.search'))} to={routes.subject(subject.id)}>
      <img className="subject-card-cover" src={getSubjectPoster(subject)} alt="" loading="lazy" />
      <span className="subject-card-body">
        <span className="subject-card-title">{getSubjectTitle(subject, t('common.untitledSubject'))}</span>
        <span className="subject-card-meta">
          {getSubjectMeta(subject, t('common.episodeUnit')) || subject.subject_type}
        </span>
      </span>
    </Link>
  );
}
