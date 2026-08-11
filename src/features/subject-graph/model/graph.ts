import {
  type SubjectCharacter,
  type SubjectDetail,
  type SubjectEpisode,
  type SubjectRelation,
  type SubjectStaff,
  type SubjectSummary,
} from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { applyGraphDensityLimits } from './graph-density';

export type GraphNodeType = 'subject' | 'episode' | 'staff' | 'character' | 'relation' | 'meta';

export type GraphNode = {
  id: string;
  label: string;
  subtitle?: string | undefined;
  details?: string[];
  type: GraphNodeType;
  size: number;
  image?: string | null;
  href?: string | undefined;
};

export type GraphEdge = {
  source: string;
  target: string;
  label: string;
  strength: number;
};

export type GraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated?: boolean;
};

export type GraphMode = 'balanced' | 'complete';

export type GraphSections = {
  episodes: boolean;
  staff: boolean;
  characters: boolean;
  relations: boolean;
  meta: boolean;
};

export const defaultGraphSections: GraphSections = {
  episodes: true,
  staff: true,
  characters: true,
  relations: true,
  meta: true,
};

export const graphSectionKeys = ['episodes', 'characters', 'staff', 'relations', 'meta'] as const;

export const graphSectionLabelKeys: Record<
  (typeof graphSectionKeys)[number],
  | 'graph.section.episodes'
  | 'graph.section.characters'
  | 'graph.section.staff'
  | 'graph.section.relations'
  | 'graph.section.meta'
> = {
  episodes: 'graph.section.episodes',
  characters: 'graph.section.characters',
  staff: 'graph.section.staff',
  relations: 'graph.section.relations',
  meta: 'graph.section.meta',
};

function titleOf(subject: SubjectDetail, fallback: string) {
  return subject.display_title || subject.title || subject.title_cn || fallback;
}

function isOpenableSubjectType(type: unknown) {
  return type === 'anime' || type === 'galgame';
}

function subjectSummaryTitle(subject: SubjectRelation['subject'], fallback: string) {
  return subject.display_title || subject.title || subject.title_cn || fallback;
}

function episodeTitle(episode: SubjectEpisode) {
  return episode.title || (episode.ep_num ? `EP ${episode.ep_num}` : `Episode ${episode.id}`);
}

function compactDetails(values: Array<unknown>) {
  return values
    .map((value) => {
      if (value === null || value === undefined || value === '') return null;
      if (Array.isArray(value)) return value.filter(Boolean).join(' / ');
      if (typeof value === 'string') return value;
      if (typeof value === 'number' || typeof value === 'bigint' || typeof value === 'boolean') return String(value);
      return null;
    })
    .filter((value): value is string => Boolean(value));
}

function stringOrNull(value: unknown) {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function imageOf(
  item:
    Pick<SubjectSummary, 'image' | 'image_original' | 'image_thumbnail' | 'images'> | SubjectStaff | SubjectCharacter,
): string | null {
  const images = item.images as { poster?: string | null; thumbnail?: string | null } | undefined;
  return (
    stringOrNull(images?.poster) ||
    stringOrNull(images?.thumbnail) ||
    stringOrNull(item.image) ||
    stringOrNull(item.image_thumbnail) ||
    stringOrNull(item.image_original)
  );
}

function addUniqueNode(nodes: Map<string, GraphNode>, node: GraphNode) {
  if (!nodes.has(node.id)) nodes.set(node.id, node);
}

function addEdge(edges: GraphEdge[], source: string, target: string, label: string, strength = 1) {
  if (source === target) return;
  const key = `${source}->${target}:${label}`;
  if (edges.some((edge) => `${edge.source}->${edge.target}:${edge.label}` === key)) return;
  edges.push({ source, target, label, strength });
}

export function buildGraph({
  characters,
  episodes,
  relations,
  sections,
  staff,
  subject,
  fallback,
}: {
  subject: SubjectDetail;
  episodes: SubjectEpisode[];
  staff: SubjectStaff[];
  characters: SubjectCharacter[];
  relations: SubjectRelation[];
  sections: GraphSections;
  fallback: string;
}): GraphData {
  const nodes = new Map<string, GraphNode>();
  const edges: GraphEdge[] = [];
  const rootId = `subject:${subject.id}`;

  addUniqueNode(nodes, {
    id: rootId,
    label: titleOf(subject, fallback),
    subtitle: [subject.subject_type, subject.platform, subject.date].filter(Boolean).join(' · '),
    details: compactDetails([
      subject.subject_type,
      subject.platform,
      subject.date,
      subject.episode_count ? `${subject.episode_count} episodes` : null,
      subject.character_count ? `${subject.character_count} characters` : null,
      subject.staff_count ? `${subject.staff_count} staff` : null,
    ]),
    type: 'subject',
    size: 46,
    image: imageOf(subject),
    href: isOpenableSubjectType(subject.subject_type) ? routes.subject(subject.id) : undefined,
  });

  if (sections.meta) {
    for (const tag of (subject.tags ?? []).slice(0, 12)) {
      const id = `tag:${tag}`;
      addUniqueNode(nodes, { id, label: tag, subtitle: 'Tag', type: 'meta', size: 11 });
      addEdge(edges, rootId, id, 'tag', 0.7);
    }

    for (const value of [subject.platform, subject.date, subject.subject_type].filter(Boolean).slice(0, 4)) {
      const label = String(value);
      const id = `meta:${label}`;
      addUniqueNode(nodes, { id, label, subtitle: 'Meta', type: 'meta', size: 12 });
      addEdge(edges, rootId, id, 'metadata', 0.65);
    }
  }

  const visibleEpisodes = sections.episodes ? episodes : [];
  const primaryEpisodes = visibleEpisodes.filter((episode) => episode.type === 'EP');
  const otherEpisodes = visibleEpisodes.filter((episode) => episode.type !== 'EP');
  for (const episode of [...primaryEpisodes, ...otherEpisodes]) {
    const id = `episode:${episode.id}`;
    addUniqueNode(nodes, {
      id,
      label: episodeTitle(episode),
      subtitle: episode.type,
      details: compactDetails([
        episode.type,
        episode.date,
        episode.ep_num ? `EP ${episode.ep_num}` : null,
        episode.sort ? `Sort ${episode.sort}` : null,
        episode.duration,
      ]),
      type: 'episode',
      size: episode.type === 'EP' ? 9 : 7,
    });
    addEdge(edges, rootId, id, episode.type || 'episode', 0.42);
  }

  for (const item of sections.staff ? staff : []) {
    const id = `staff:${item.id}`;
    addUniqueNode(nodes, {
      id,
      label: item.name_cn || item.name,
      subtitle: item.role || item.type || undefined,
      details: compactDetails([item.role, item.type, item.gender, stringOrNull(item.birth)]),
      type: 'staff',
      size: imageOf(item) ? 18 : 13,
      image: imageOf(item),
    });
    addEdge(edges, rootId, id, item.role || 'staff', 0.78);
  }

  for (const character of sections.characters ? characters : []) {
    const isMain = character.role?.toLowerCase().includes('main') || character.role?.includes('主');
    const id = `character:${character.id}`;
    addUniqueNode(nodes, {
      id,
      label: character.name_cn || character.name,
      subtitle: character.role || character.type || undefined,
      details: compactDetails([
        character.role,
        character.type,
        character.gender,
        character.actors?.slice(0, 3).map((actor) => actor.name_cn || actor.name),
      ]),
      type: 'character',
      size: isMain ? 24 : 18,
      image: imageOf(character),
    });
    addEdge(edges, rootId, id, character.role || 'character', 0.9);

    for (const actor of sections.staff ? (character.actors ?? []).slice(0, 3) : []) {
      const actorId = `staff:${actor.id}`;
      addUniqueNode(nodes, {
        id: actorId,
        label: actor.name_cn || actor.name,
        subtitle: actor.role || actor.type || 'Voice',
        details: compactDetails([actor.role || 'Voice', actor.type, actor.gender, stringOrNull(actor.birth)]),
        type: 'staff',
        size: imageOf(actor) ? 16 : 11,
        image: imageOf(actor),
      });
      addEdge(edges, id, actorId, 'voice', 0.62);
    }
  }

  for (const relation of sections.relations ? relations : []) {
    const related = relation.subject;
    const id = `relation:${related.id}`;
    addUniqueNode(nodes, {
      id,
      label: subjectSummaryTitle(related, fallback),
      subtitle: [relation.relation, related.subject_type, related.date].filter(Boolean).join(' · '),
      details: compactDetails([
        relation.relation,
        related.subject_type,
        related.platform,
        related.date,
        related.content?.episodes ? `${related.content.episodes} episodes` : null,
      ]),
      type: 'relation',
      size: related.subject_type === subject.subject_type ? 30 : 24,
      image: imageOf(related),
      href: isOpenableSubjectType(related.subject_type) ? routes.subject(related.id) : undefined,
    });
    addEdge(edges, rootId, id, relation.relation || 'related', 0.9);
  }

  return applyGraphDensityLimits({ nodes: [...nodes.values()], edges });
}
