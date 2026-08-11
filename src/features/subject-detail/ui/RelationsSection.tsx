import { useId, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { subjectQueries } from '@/entities/subject';
import type { SubjectRelation, UUID } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { Link, useLocation } from '@tanstack/react-router';
import { routes } from '@/shared/routing/paths';
import { routeBackState } from '@/shared/routing/route-state';
import { Button } from '@/shared/ui/Button';
import { DetailSection } from '@/shared/ui/Detail';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/ui/Dialog';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Pagination } from '@/shared/ui/Pagination';
import {
  detailRows,
  groupRelationsForDisplay,
  isPrimaryRelation,
  paginateRelationGroups,
  relationTitle,
} from '../model/subject-detail';
import { RelationItemContent } from './RelationItemContent';
import { DetailShell } from './SubjectDetailPrimitives';

export function RelationsSection({
  className,
  subjectId,
  subjectTitle,
}: {
  className?: string;
  subjectId: UUID;
  subjectTitle: string;
}) {
  const { t } = useI18n();
  const location = useLocation();
  const emptyText = t('common.none');
  const sectionTitleId = useId();
  const [page, setPage] = useState(1);
  const [relation, setRelation] = useState<SubjectRelation | null>(null);
  const query = useQuery(subjectQueries.allRelations(subjectId));
  const groups = groupRelationsForDisplay(query.data ?? [], t('subject.related'));
  const pages = paginateRelationGroups(groups);
  const currentPage = Math.max(1, Math.min(page, pages.length || 1));
  const visibleGroups = pages[currentPage - 1] ?? [];
  const rows = groups.flatMap((group) => group.items);
  const detailLinkState = routeBackState(location, subjectTitle);

  return (
    <>
      <DetailSection
        className={className}
        id="relations"
        meta={
          query.isFetching && rows.length === 0
            ? t('subject.loadingRelatedSubjects')
            : `${rows.length} ${t('subject.relatedSubjects')}`
        }
        title={t('subject.relations')}
        titleId={sectionTitleId}
      >
        {query.isFetching && rows.length === 0 ? (
          <LoadingState title={t('subject.loadingRelations')} description={t('subject.loadingRelationsBody')} />
        ) : null}
        {query.isError ? (
          <ErrorState
            action={
              <Button size="sm" variant="secondary" onClick={() => void query.refetch()}>
                {t('common.retry')}
              </Button>
            }
            description={t('subject.relationsErrorBody')}
            title={t('subject.relationsErrorTitle')}
          />
        ) : null}
        {!query.isFetching && !query.isError && rows.length === 0 ? <EmptyState title={emptyText} /> : null}
        {rows.length > 0 ? (
          <div className="grid gap-5">
            {visibleGroups.map((group, groupIndex) => {
              const groupTitleId = `${sectionTitleId}-group-${currentPage}-${groupIndex}`;
              return (
                <section aria-labelledby={groupTitleId} className="grid gap-2.5" key={group.key}>
                  <div className="flex min-w-0 items-baseline justify-between gap-3">
                    <h3 className="m-0 truncate text-sm font-semibold text-foreground" id={groupTitleId}>
                      {group.label}
                    </h3>
                    <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                      {group.items.length === group.totalCount
                        ? group.items.length
                        : `${group.items.length}/${group.totalCount}`}
                    </span>
                  </div>
                  <ul className="m-0 grid list-none gap-2 p-0 sm:grid-cols-2 xl:grid-cols-3">
                    {group.items.map((item) => {
                      const key = `${item.direction}-${item.relation}-${item.subject.id}`;
                      const content = (
                        <RelationItemContent
                          emptyText={emptyText}
                          relation={item}
                          titleFallback={t('common.untitledSubject')}
                        />
                      );
                      return isPrimaryRelation(item) ? (
                        <li className="min-w-0" key={key}>
                          <Link
                            className="group grid min-h-24 grid-cols-[52px_minmax(0,1fr)] items-center gap-3 rounded-sm border border-border bg-surface p-2.5 text-left transition-colors hover:border-[var(--ui-border-strong)] hover:bg-muted"
                            state={detailLinkState}
                            to={routes.subject(item.subject.id)}
                          >
                            {content}
                          </Link>
                        </li>
                      ) : (
                        <li className="min-w-0" key={key}>
                          <Button
                            aria-haspopup="dialog"
                            className="group grid min-h-24 w-full grid-cols-[52px_minmax(0,1fr)] items-center gap-3 rounded-sm border border-border bg-surface p-2.5 text-left transition-colors hover:border-[var(--ui-border-strong)] hover:bg-muted"
                            type="button"
                            variant="unstyled"
                            onClick={() => {
                              setRelation(item);
                            }}
                          >
                            {content}
                          </Button>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              );
            })}
          </div>
        ) : null}
        {rows.length > 0 ? (
          <Pagination currentPage={currentPage} totalPages={pages.length} onPageChange={setPage} />
        ) : null}
      </DetailSection>

      <Dialog
        open={Boolean(relation)}
        onOpenChange={(open) => {
          if (!open) setRelation(null);
        }}
      >
        <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-2xl overflow-y-auto">
          {relation ? (
            <>
              <DialogHeader>
                <DialogTitle>{relationTitle(relation, t('common.untitledSubject'))}</DialogTitle>
                <DialogDescription>
                  {[relation.subject.subject_type, relation.relation || t('subject.related')]
                    .filter(Boolean)
                    .join(' · ')}
                </DialogDescription>
              </DialogHeader>
              <DetailShell
                image={relation.subject.image_original || relation.subject.image_thumbnail}
                title={relationTitle(relation, t('common.untitledSubject'))}
                subtitle={[relation.relation || t('subject.related'), relation.subject.subject_type]
                  .filter(Boolean)
                  .join(' · ')}
                description={relation.subject.description}
                emptyLabel={emptyText}
                rows={detailRows([
                  [t('subject.type'), relation.subject.subject_type],
                  [t('subject.relation'), relation.relation],
                  [t('subject.direction'), relation.direction],
                  [t('subject.date'), relation.subject.date],
                  [t('subject.platform'), relation.subject.platform],
                ])}
              />
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
