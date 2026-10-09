import { SubjectPosterCard } from '@/entities/subject';
import type { SubjectSummary } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { subjectKindLabel } from '@/shared/i18n/subject-labels';
import { routes } from '@/shared/routing/paths';
import type { RouteBackState } from '@/shared/routing/route-state';

function titleOf(item: Pick<SubjectSummary, 'display_title' | 'title' | 'title_cn'>, fallback: string) {
  return item.display_title || item.title || item.title_cn || fallback;
}

function subjectPosterOf(subject: SubjectSummary) {
  return subject.images?.poster || subject.images?.thumbnail || subject.image_thumbnail || subject.image || null;
}

export function SearchResultsGrid({ state, subjects }: { state: RouteBackState; subjects: SubjectSummary[] }) {
  const { t } = useI18n();

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {subjects.map((subject) => (
        <SubjectPosterCard
          key={subject.id}
          poster={subjectPosterOf(subject)}
          seed={subject.id}
          state={state}
          subtitle={subjectKindLabel(subject.display_subtitle || subject.subject_type, t)}
          title={titleOf(subject, t('common.untitledSubject'))}
          to={routes.entity(subject.id)}
        />
      ))}
    </div>
  );
}
