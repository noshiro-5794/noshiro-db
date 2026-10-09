import { DEFAULT_ACCENT_COLOR } from '@/shared/theme/theme-config';
import type { GraphNodeType } from '../model/graph';

export const graphNodeColors: Record<GraphNodeType, string> = {
  subject: '#d6d6da',
  episode: '#85858f',
  staff: DEFAULT_ACCENT_COLOR,
  character: '#5c9277',
  relation: '#6688a8',
  meta: '#9a825a',
};

export const graphNodeLabelKeys = {
  subject: 'graph.subjectNode',
  episode: 'graph.episodeNode',
  staff: 'graph.staffNode',
  character: 'graph.characterNode',
  relation: 'graph.relationNode',
  meta: 'graph.metaNode',
} as const satisfies Record<GraphNodeType, string>;
