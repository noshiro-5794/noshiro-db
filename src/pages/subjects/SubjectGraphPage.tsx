import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { subjectQueries } from '@/entities/subject';
import {
  buildGraph,
  defaultGraphSections,
  GraphCanvas,
  graphSectionKeys,
  graphSectionLabelKeys,
  loadGraphPayload,
  type GraphMode,
  type GraphSections,
} from '@/features/subject-graph';
import type { SubjectDetail } from '@/shared/api';
import { useI18n } from '@/shared/i18n';
import { parseUuid } from '@/shared/lib/validation';
import { getRouteApi, Link } from '@tanstack/react-router';
import { routes } from '@/shared/routing/paths';
import { Seo } from '@/shared/seo/Seo';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { Toggle, ToggleGroup } from '@/shared/ui/Toggle';

const subjectGraphRoute = getRouteApi('/subjects/$subjectId/graph');

function subjectTitle(subject: SubjectDetail | undefined, fallback: string) {
  return subject?.display_title || subject?.title || subject?.title_cn || fallback;
}

export function SubjectGraphPage() {
  const { t } = useI18n();
  const params = subjectGraphRoute.useParams();
  const subjectId = parseUuid(params.subjectId) ?? '';
  const [mode, setMode] = useState<GraphMode>('balanced');
  const [sections, setSections] = useState<GraphSections>(defaultGraphSections);
  const subjectQuery = useQuery({ ...subjectQueries.detail(subjectId), enabled: Boolean(subjectId) });
  const graphPayloadQuery = useQuery({
    queryKey: [...subjectQueries.detail(subjectId).queryKey, 'graph-payload', mode, sections],
    queryFn: ({ signal }) => loadGraphPayload(subjectId, mode, sections, signal),
    enabled: Boolean(subjectId),
  });

  const subject = subjectQuery.data;
  const graph = useMemo(() => {
    if (!subject) return null;
    return buildGraph({
      subject,
      episodes: graphPayloadQuery.data?.episodes ?? [],
      staff: graphPayloadQuery.data?.staff ?? [],
      characters: graphPayloadQuery.data?.characters ?? [],
      relations: graphPayloadQuery.data?.relations ?? [],
      sections,
      fallback: t('common.untitledSubject'),
    });
  }, [graphPayloadQuery.data, sections, subject, t]);

  const isLoading = subjectQuery.isLoading || graphPayloadQuery.isLoading;
  const isError = subjectQuery.isError || graphPayloadQuery.isError;
  const layerCounts: Record<(typeof graphSectionKeys)[number], number> = {
    episodes: graphPayloadQuery.data?.episodes.length ?? 0,
    characters: graphPayloadQuery.data?.characters.length ?? 0,
    staff: graphPayloadQuery.data?.staff.length ?? 0,
    relations: graphPayloadQuery.data?.relations.length ?? 0,
    meta:
      (subject?.tags?.length ?? 0) + [subject?.platform, subject?.date, subject?.subject_type].filter(Boolean).length,
  };

  return (
    <section className="graph-fullscreen" data-slot="subject-graph-page">
      <Seo
        title={`${subjectTitle(subject, t('subject.title'))} · ${t('graph.title')}`}
        description={subject?.description_excerpt || subject?.summary || t('graph.description')}
        image={subject?.images?.poster || subject?.image || subject?.image_thumbnail}
        path={subjectId ? routes.subjectGraph(subjectId) : undefined}
      />
      <div className="graph-back" data-slot="graph-back">
        <Button asChild aria-label={t('common.back')} size="icon" tooltip={t('common.back')} variant="secondary">
          {subjectId ? (
            <Link params={{ subjectId }} to="/subjects/$subjectId">
              <ArrowLeft className="size-4" />
            </Link>
          ) : (
            <Link to={routes.search}>
              <ArrowLeft className="size-4" />
            </Link>
          )}
        </Button>
      </div>
      <div className="graph-data-controls" data-slot="graph-data-controls">
        <div className="graph-control-block" data-slot="graph-control-block">
          <span className="graph-control-label">{t('graph.mode')}</span>
          <ToggleGroup
            aria-label={t('graph.mode')}
            className="graph-mode-switch !grid grid-cols-2 !bg-inset"
            value={[mode]}
            onValueChange={(values) => {
              const nextMode = values[0];
              if (nextMode === 'balanced' || nextMode === 'complete') setMode(nextMode);
            }}
          >
            {(['balanced', 'complete'] as const).map((value) => (
              <Toggle key={value} value={value} variant="bare">
                {t(value === 'balanced' ? 'graph.modeBalanced' : 'graph.modeComplete')}
              </Toggle>
            ))}
          </ToggleGroup>
        </div>
        <div className="graph-control-block graph-control-block-wide" data-slot="graph-layer-controls">
          <span className="graph-control-label">{t('graph.layers')}</span>
          <ToggleGroup
            multiple
            aria-label={t('graph.layers')}
            className="graph-section-toggles !grid grid-cols-2 gap-1 !border-0 !bg-transparent !p-0"
            value={graphSectionKeys.filter((key) => sections[key])}
            onValueChange={(values) => {
              const enabledSections = new Set(values);
              setSections({
                episodes: enabledSections.has('episodes'),
                staff: enabledSections.has('staff'),
                characters: enabledSections.has('characters'),
                relations: enabledSections.has('relations'),
                meta: enabledSections.has('meta'),
              });
            }}
          >
            {graphSectionKeys.map((key) => (
              <Toggle key={key} value={key} variant="bare">
                <span>{t(graphSectionLabelKeys[key])}</span>
                <small className="graph-section-count">{layerCounts[key]}</small>
              </Toggle>
            ))}
          </ToggleGroup>
        </div>
        <div className="graph-control-stats" data-slot="graph-control-stats">
          <strong>{graph?.nodes.length ?? 0}</strong>
          <span>{t('graph.nodes')}</span>
          <strong>{graph?.edges.length ?? 0}</strong>
          <span>{t('graph.edges')}</span>
        </div>
      </div>
      {isLoading ? (
        <div className="graph-state">
          <LoadingState title={t('graph.loading')} />
        </div>
      ) : null}
      {isError ? (
        <div className="graph-state">
          <ErrorState title={t('subject.errorTitle')} description={t('subject.errorBody')} />
        </div>
      ) : null}
      {!isLoading && !isError && graph && graph.nodes.length <= 1 ? (
        <div className="graph-state">
          <EmptyState title={t('graph.emptyTitle')} description={t('graph.emptyBody')} />
        </div>
      ) : null}
      {!isLoading && !isError && graph && graph.nodes.length > 1 ? <GraphCanvas graph={graph} /> : null}
    </section>
  );
}
