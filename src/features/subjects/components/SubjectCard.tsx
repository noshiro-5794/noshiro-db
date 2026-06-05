import { Link, useLocation } from 'react-router-dom';
import type { Locale } from '@/features/i18n/messages';
import { useI18n } from '@/features/i18n/use-i18n';
import type { SubjectSummary } from '@/lib/api/types';
import { routes } from '@/routes/paths';
import { routeBackState } from '@/shared/navigation/route-state';

const coverPlaceholder = '/assets/placeholders/subject-cover.png';
const episodeUnit: Record<Locale, string> = {
  'zh-CN': '话',
  'en-US': 'episodes',
  'ja-JP': '話',
};

function getSubjectTitle(subject: SubjectSummary, fallback: string) {
  return subject.display_title || subject.title || subject.title_cn || fallback;
}

function getSubjectPoster(subject: SubjectSummary) {
  return subject.images?.poster || subject.images?.thumbnail || subject.image_thumbnail || subject.image || coverPlaceholder;
}

function getSubjectMeta(subject: SubjectSummary, locale: Locale) {
  return subject.display_subtitle || subject.display_meta?.join(' / ') || [
    subject.content?.episodes ? `${subject.content.episodes} ${episodeUnit[locale]}` : null,
    subject.year ? `${subject.year}` : subject.date,
    subject.platform,
  ].filter(Boolean).join(' / ');
}

type SubjectCardProps = {
  subject: SubjectSummary;
};

export function SubjectCard({ subject }: SubjectCardProps) {
  const { locale, t } = useI18n();
  const location = useLocation();

  return (
    <Link className="subject-card" state={routeBackState(location, t('nav.search'))} to={routes.subject(subject.id)}>
      <img
        className="subject-card-cover"
        src={getSubjectPoster(subject)}
        alt=""
        loading="lazy"
      />
      <span className="subject-card-body">
        <span className="subject-card-title">{getSubjectTitle(subject, t('common.untitledSubject'))}</span>
        <span className="subject-card-meta">{getSubjectMeta(subject, locale) || subject.subject_type}</span>
      </span>
    </Link>
  );
}
