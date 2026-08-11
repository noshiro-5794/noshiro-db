import type { SubjectRelation } from '@/shared/api';
import { Badge } from '@/shared/ui/Badge';
import { isPrimaryRelation, relationMeta, relationTitle, subjectImage } from '../model/subject-detail';

export function RelationItemContent({
  emptyText,
  relation,
  titleFallback,
}: {
  emptyText: string;
  relation: SubjectRelation;
  titleFallback: string;
}) {
  return (
    <>
      <img
        alt=""
        className="h-[72px] w-[52px] rounded-sm bg-muted object-cover ring-1 ring-inset ring-border-subtle"
        decoding="async"
        loading="lazy"
        referrerPolicy="no-referrer"
        src={subjectImage(relation.subject)}
      />
      <span className="grid min-w-0 gap-1.5">
        <span className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge variant={isPrimaryRelation(relation) ? 'accent' : 'secondary'}>
            {relation.subject.subject_type || emptyText}
          </Badge>
        </span>
        <span className="line-clamp-2 text-sm font-semibold leading-5 text-foreground group-hover:text-[var(--ui-accent-text)]">
          {relationTitle(relation, titleFallback)}
        </span>
        <span className="line-clamp-1 text-xs text-muted-foreground sm:text-sm">
          {relationMeta(relation, emptyText)}
        </span>
      </span>
    </>
  );
}
