import { useEffect, useMemo, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { Link, useNavigate, useParams } from '@/shared/routing/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Maximize2, Minus, Plus, RotateCcw } from 'lucide-react';
import { indexApi } from '@/entities/subject';
import { subjectQueries } from '@/entities/subject';
import type {
  ApiPage,
  PageQuery,
  SubjectCharacter,
  SubjectDetail,
  SubjectEpisode,
  SubjectRelation,
  SubjectStaff,
  SubjectSummary,
  UUID,
} from '@/shared/api';
import { routes } from '@/shared/routing/paths';
import { Seo } from '@/shared/seo/Seo';
import { Button } from '@/shared/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui/FeedbackState';
import { useI18n } from '@/shared/i18n';

type GraphNodeType = 'subject' | 'episode' | 'staff' | 'character' | 'relation' | 'meta';

type GraphNode = {
  id: string;
  label: string;
  subtitle?: string;
  details?: string[];
  type: GraphNodeType;
  size: number;
  image?: string | null;
  href?: string;
};

type GraphEdge = {
  source: string;
  target: string;
  label: string;
  strength: number;
};

type GraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

type SimNode = GraphNode & {
  x: number;
  y: number;
  vx: number;
  vy: number;
  pinned?: boolean;
};

type DragState = {
  node: SimNode;
  startX: number;
  startY: number;
  moved: boolean;
};

type GraphPayload = {
  episodes: SubjectEpisode[];
  staff: SubjectStaff[];
  characters: SubjectCharacter[];
  relations: SubjectRelation[];
};

type GraphMode = 'balanced' | 'complete';

type GraphSections = {
  episodes: boolean;
  staff: boolean;
  characters: boolean;
  relations: boolean;
  meta: boolean;
};

type CachedImage = {
  image: HTMLImageElement;
  ready: boolean;
};

type ViewTransform = {
  scale: number;
  offsetX: number;
  offsetY: number;
};

function subjectTitle(subject: SubjectDetail | undefined, fallback: string) {
  return subject?.display_title || subject?.title || subject?.title_cn || fallback;
}

type PanState = {
  startX: number;
  startY: number;
  offsetX: number;
  offsetY: number;
};

const nodeColors: Record<GraphNodeType, string> = {
  subject: '#f9fafb',
  episode: '#94a3b8',
  staff: '#7F6FB0',
  character: '#22c55e',
  relation: '#38bdf8',
  meta: '#f59e0b',
};

const defaultGraphSections: GraphSections = {
  episodes: true,
  staff: true,
  characters: true,
  relations: true,
  meta: true,
};

const graphSectionKeys = ['episodes', 'characters', 'staff', 'relations', 'meta'] as const;

const graphSectionLabelKeys: Record<
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

const graphNodeLabelKeys: Record<
  GraphNodeType,
  | 'graph.subjectNode'
  | 'graph.staffNode'
  | 'graph.characterNode'
  | 'graph.episodeNode'
  | 'graph.relationNode'
  | 'graph.metaNode'
> = {
  subject: 'graph.subjectNode',
  episode: 'graph.episodeNode',
  staff: 'graph.staffNode',
  character: 'graph.characterNode',
  relation: 'graph.relationNode',
  meta: 'graph.metaNode',
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
  const images =
    typeof item.images === 'object' && item.images
      ? (item.images as { poster?: string | null; thumbnail?: string | null })
      : null;
  return (
    stringOrNull(images?.poster) ||
    stringOrNull(images?.thumbnail) ||
    stringOrNull(item.image) ||
    stringOrNull(item.image_thumbnail) ||
    stringOrNull(item.image_original)
  );
}

function hashNumber(value: string) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 4294967295;
}

function initialRadius(type: GraphNodeType, width: number, height: number) {
  const base = Math.min(width, height);
  switch (type) {
    case 'subject':
      return 0;
    case 'meta':
      return base * 0.14;
    case 'character':
    case 'staff':
      return base * 0.22;
    case 'relation':
      return base * 0.29;
    case 'episode':
      return base * 0.34;
  }
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

async function loadPages<T>(
  fetchPage: (query: PageQuery) => Promise<ApiPage<T>>,
  pageSize = 120,
  maxPages = Number.POSITIVE_INFINITY,
) {
  const results: T[] = [];
  for (let page = 1; page <= Math.max(1, maxPages); page += 1) {
    const response = await fetchPage({ page, page_size: pageSize });
    results.push(...response.results);
    if (!response.next || results.length >= response.count) break;
  }

  return results;
}

async function loadGraphPayload(subjectId: UUID, mode: GraphMode, sections: GraphSections): Promise<GraphPayload> {
  const pageSize = mode === 'complete' ? 160 : 72;
  const maxPages = mode === 'complete' ? Number.POSITIVE_INFINITY : 1;
  const [episodes, staff, characters, relations] = await Promise.all([
    sections.episodes
      ? loadPages((query) => indexApi.listSubjectEpisodes(subjectId, query), pageSize, maxPages)
      : Promise.resolve([]),
    sections.staff
      ? loadPages((query) => indexApi.listSubjectStaff(subjectId, query), pageSize, maxPages)
      : Promise.resolve([]),
    sections.characters
      ? loadPages((query) => indexApi.listSubjectCharacters(subjectId, query), pageSize, maxPages)
      : Promise.resolve([]),
    sections.relations
      ? loadPages((query) => indexApi.listSubjectRelations(subjectId, query), pageSize, maxPages)
      : Promise.resolve([]),
  ]);

  return { episodes, staff, characters, relations };
}

function buildGraph({
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

  const primaryEpisodes = episodes.filter((episode) => episode.type === 'EP');
  const otherEpisodes = episodes.filter((episode) => episode.type !== 'EP');
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

  for (const item of staff) {
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

  for (const character of characters) {
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

    for (const actor of (character.actors ?? []).slice(0, 3)) {
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

  for (const relation of relations) {
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

  return normalizeGraphDensity({ nodes: [...nodes.values()], edges });
}

function normalizeGraphDensity(graph: GraphData): GraphData {
  const count = graph.nodes.length;
  const pressure = count > 520 ? 0.58 : count > 360 ? 0.68 : count > 220 ? 0.8 : count > 140 ? 0.9 : 1;
  return {
    ...graph,
    nodes: graph.nodes.map((node) => {
      if (node.type === 'subject') return node;
      const imageBoost = node.image ? 1.08 : 1;
      const typeFloor = node.type === 'episode' ? 6 : node.type === 'meta' ? 8 : 10;
      return {
        ...node,
        size: Math.max(typeFloor, Math.round(node.size * pressure * imageBoost)),
      };
    }),
  };
}

function drawGraph({
  canvas,
  edges,
  hoveredId,
  imageCache,
  nodes,
  selectedId,
  time,
  view,
}: {
  canvas: HTMLCanvasElement;
  nodes: SimNode[];
  edges: GraphEdge[];
  imageCache: Map<string, CachedImage>;
  hoveredId?: string;
  selectedId?: string;
  time: number;
  view: ViewTransform;
}) {
  const context = canvas.getContext('2d');
  if (!context) return;

  const width = canvas.width;
  const height = canvas.height;
  const dpr = window.devicePixelRatio || 1;
  context.clearRect(0, 0, width, height);
  context.save();
  context.scale(dpr, dpr);
  const viewWidth = width / dpr;
  const viewHeight = height / dpr;

  const gradient = context.createLinearGradient(0, 0, viewWidth, viewHeight);
  gradient.addColorStop(0, 'rgba(18,18,22,1)');
  gradient.addColorStop(0.45, 'rgba(11,11,14,1)');
  gradient.addColorStop(1, 'rgba(20,18,28,1)');
  context.fillStyle = gradient;
  context.fillRect(0, 0, viewWidth, viewHeight);
  drawTechnicalBackdrop(context, viewWidth, viewHeight, time);

  context.save();
  context.translate(view.offsetX, view.offsetY);
  context.scale(view.scale, view.scale);

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  for (const edge of edges) {
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (!source || !target) continue;
    const highlighted = Boolean(
      (hoveredId && (edge.source === hoveredId || edge.target === hoveredId)) ||
      (selectedId && (edge.source === selectedId || edge.target === selectedId)),
    );
    context.strokeStyle = highlighted ? 'rgba(255,255,255,0.72)' : 'rgba(255,255,255,0.13)';
    context.lineWidth = highlighted ? 1.6 : 0.9;
    context.beginPath();
    context.moveTo(source.x, source.y);
    context.lineTo(target.x, target.y);
    context.stroke();
  }

  for (const node of nodes) {
    const highlighted = hoveredId === node.id || selectedId === node.id;
    if (highlighted || node.pinned) {
      const color = nodeColors[node.type];
      context.strokeStyle = colorWithAlpha(color, highlighted ? 0.42 : 0.24);
      context.lineWidth = highlighted ? 2 : 1;
      context.beginPath();
      context.arc(node.x, node.y, node.size + 8 + Math.sin(time / 180) * 1.4, 0, Math.PI * 2);
      context.stroke();
    }
    drawNode(context, node, imageCache, highlighted);

    if (highlighted || node.type === 'subject' || node.size >= 15) {
      context.font =
        node.type === 'subject' ? '650 14px Inter, system-ui, sans-serif' : '600 11px Inter, system-ui, sans-serif';
      context.fillStyle = 'rgba(255,255,255,0.92)';
      context.textAlign = 'center';
      const labelY =
        node.type === 'subject' || node.type === 'relation' ? node.y + node.size + 26 : node.y - node.size - 10;
      context.fillText(node.label.slice(0, 28), node.x, labelY);
    }
  }
  context.restore();
  context.restore();
}

function drawTechnicalBackdrop(context: CanvasRenderingContext2D, width: number, height: number, time: number) {
  const drift = time / 9000;
  context.save();
  context.lineWidth = 1;

  for (let row = 0; row < 12; row += 1) {
    const baseY = (height / 11) * row;
    context.beginPath();
    for (let x = -40; x <= width + 40; x += 28) {
      const y =
        baseY + Math.sin(x * 0.008 + row * 0.72 + drift) * 22 + Math.sin(x * 0.017 - row * 0.45 + drift * 0.7) * 8;
      if (x === -40) context.moveTo(x, y);
      else context.lineTo(x, y);
    }
    context.strokeStyle = row % 3 === 0 ? 'rgba(127,111,176,0.08)' : 'rgba(255,255,255,0.032)';
    context.stroke();
  }

  for (let index = 0; index < 9; index += 1) {
    const x = (width / 8) * index;
    context.beginPath();
    context.moveTo(x - 160, height);
    context.bezierCurveTo(x + 80, height * 0.72, x - 120, height * 0.32, x + 120, 0);
    context.strokeStyle = index % 2 === 0 ? 'rgba(56,189,248,0.04)' : 'rgba(255,255,255,0.024)';
    context.stroke();
  }

  context.restore();
}

function drawNode(
  context: CanvasRenderingContext2D,
  node: SimNode,
  imageCache: Map<string, CachedImage>,
  highlighted: boolean,
) {
  const color = nodeColors[node.type];
  const cached = node.image ? imageCache.get(node.image) : null;
  const image = cached?.ready ? cached.image : null;
  context.save();
  context.shadowColor = color;
  context.shadowBlur = highlighted || node.type === 'subject' ? 22 : 7;

  if (node.type === 'subject' || node.type === 'relation') {
    const width = node.type === 'subject' ? node.size * 1.36 : node.size * 1.28;
    const height = node.type === 'subject' ? node.size * 1.92 : node.size * 1.82;
    const x = node.x - width / 2;
    const y = node.y - height / 2;
    context.fillStyle = 'rgba(255,255,255,0.08)';
    context.beginPath();
    context.roundRect(x, y, width, height, 8);
    context.fill();
    context.clip();
    if (image) {
      drawCoverImage(context, image, x, y, width, height);
    } else {
      context.fillStyle = colorWithAlpha(color, 0.58);
      context.fillRect(x, y, width, height);
    }
    context.restore();
    context.save();
    context.strokeStyle = highlighted ? 'rgba(255,255,255,0.9)' : colorWithAlpha(color, 0.42);
    context.lineWidth = highlighted ? 2 : 1;
    context.beginPath();
    context.roundRect(x, y, width, height, 8);
    context.stroke();
    context.restore();
    return;
  }

  if (node.type === 'character' || node.type === 'staff') {
    context.beginPath();
    context.arc(node.x, node.y, highlighted ? node.size + 2 : node.size, 0, Math.PI * 2);
    context.fillStyle = colorWithAlpha(color, image ? 0.22 : 0.86);
    context.fill();
    context.clip();
    if (image) {
      drawCoverImage(context, image, node.x - node.size, node.y - node.size, node.size * 2, node.size * 2);
    }
    context.restore();
    context.save();
    context.strokeStyle = highlighted ? 'rgba(255,255,255,0.88)' : colorWithAlpha(color, 0.56);
    context.lineWidth = highlighted ? 2 : 1;
    context.beginPath();
    context.arc(node.x, node.y, highlighted ? node.size + 2 : node.size, 0, Math.PI * 2);
    context.stroke();
    context.restore();
    return;
  }

  if (node.type === 'episode') {
    const width = Math.max(34, Math.min(74, 28 + node.label.length * 3.2));
    const height = 18;
    context.fillStyle = highlighted ? 'rgba(255,255,255,0.88)' : 'rgba(148,163,184,0.22)';
    context.strokeStyle = highlighted ? 'rgba(255,255,255,0.72)' : 'rgba(148,163,184,0.28)';
    context.lineWidth = 1;
    context.beginPath();
    context.roundRect(node.x - width / 2, node.y - height / 2, width, height, 999);
    context.fill();
    context.stroke();
    context.fillStyle = highlighted ? '#111827' : 'rgba(255,255,255,0.68)';
    context.font = '700 9px Inter, system-ui, sans-serif';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(node.label.slice(0, 12), node.x, node.y + 0.5);
    context.restore();
    return;
  }

  context.fillStyle = highlighted ? color : colorWithAlpha(color, 0.72);
  context.beginPath();
  context.arc(node.x, node.y, highlighted ? node.size + 2 : node.size, 0, Math.PI * 2);
  context.fill();
  context.restore();
}

function drawCoverImage(
  context: CanvasRenderingContext2D,
  image: HTMLImageElement,
  x: number,
  y: number,
  width: number,
  height: number,
) {
  const ratio = Math.max(width / image.naturalWidth, height / image.naturalHeight);
  const drawWidth = image.naturalWidth * ratio;
  const drawHeight = image.naturalHeight * ratio;
  context.drawImage(image, x + (width - drawWidth) / 2, y + (height - drawHeight) / 2, drawWidth, drawHeight);
}

function warmImageCache(nodes: SimNode[], imageCache: Map<string, CachedImage>) {
  for (const node of nodes) {
    if (!node.image || imageCache.has(node.image)) continue;
    const image = new Image();
    const cached = { image, ready: false };
    image.onload = () => {
      cached.ready = true;
    };
    image.src = node.image;
    imageCache.set(node.image, cached);
  }
}

function colorWithAlpha(hex: string, alpha: number) {
  const value = hex.replace('#', '');
  const red = Number.parseInt(value.slice(0, 2), 16);
  const green = Number.parseInt(value.slice(2, 4), 16);
  const blue = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${red},${green},${blue},${alpha})`;
}

function tick(nodes: SimNode[], edges: GraphEdge[], width: number, height: number) {
  const area = Math.max(1, width * height);
  const k = Math.sqrt(area / Math.max(1, nodes.length)) * 0.62;
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const stride = nodes.length > 520 ? 4 : nodes.length > 340 ? 3 : nodes.length > 220 ? 2 : 1;

  for (let index = 0; index < nodes.length; index += 1) {
    const a = nodes[index];
    for (let otherIndex = index + 1; otherIndex < nodes.length; otherIndex += stride) {
      const b = nodes[otherIndex];
      const dx = a.x - b.x || 0.01;
      const dy = a.y - b.y || 0.01;
      const distance = Math.max(16, Math.hypot(dx, dy));
      const collisionDistance = a.size + b.size + 24;
      const collisionBoost =
        distance < collisionDistance ? 1 + ((collisionDistance - distance) / collisionDistance) * 5 : 1;
      const force = ((k * k) / distance) * 0.00175 * collisionBoost;
      const fx = (dx / distance) * force;
      const fy = (dy / distance) * force;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }
  }

  for (const edge of edges) {
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (!source || !target) continue;
    const dx = target.x - source.x || 0.01;
    const dy = target.y - source.y || 0.01;
    const distance = Math.max(1, Math.hypot(dx, dy));
    const rootEdge = source.type === 'subject' || target.type === 'subject';
    const ideal = k * (rootEdge ? 1.85 : 1.95) + source.size + target.size;
    const force = ((distance - ideal) / ideal) * (rootEdge ? 0.024 : 0.024) * edge.strength;
    const fx = (dx / distance) * force;
    const fy = (dy / distance) * force;
    source.vx += fx;
    source.vy += fy;
    target.vx -= fx;
    target.vy -= fy;
  }

  for (const node of nodes) {
    if (node.pinned) {
      node.vx *= 0.28;
      node.vy *= 0.28;
      continue;
    }

    const centerX = width / 2;
    const centerY = height / 2;
    const toCenterX = centerX - node.x;
    const toCenterY = centerY - node.y;
    const radialDistance = Math.max(1, Math.hypot(toCenterX, toCenterY));
    const safeRadius = Math.min(width, height) * (node.type === 'subject' ? 0.05 : 0.38);

    if (node.type === 'subject') {
      node.vx += toCenterX * 0.02;
      node.vy += toCenterY * 0.02;
    } else {
      const overflow = Math.max(0, radialDistance - safeRadius);
      const radialStrength = 0.0011 + (overflow / Math.max(1, safeRadius)) * 0.018;
      node.vx += toCenterX * radialStrength;
      node.vy += toCenterY * radialStrength;
    }

    const padding = node.type === 'subject' ? 96 : 72;
    if (node.x < padding) node.vx += (padding - node.x) * 0.06;
    if (node.x > width - padding) node.vx -= (node.x - (width - padding)) * 0.06;
    if (node.y < padding) node.vy += (padding - node.y) * 0.06;
    if (node.y > height - padding) node.vy -= (node.y - (height - padding)) * 0.06;

    node.vx *= 0.8;
    node.vy *= 0.8;
    node.x = Math.min(width - 28, Math.max(28, node.x + node.vx));
    node.y = Math.min(height - 28, Math.max(28, node.y + node.vy));
  }
}

function GraphCanvas({ graph }: { graph: GraphData }) {
  const { t } = useI18n();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const imageCacheRef = useRef(new Map<string, CachedImage>());
  const dragRef = useRef<DragState | null>(null);
  const panRef = useRef<PanState | null>(null);
  const hoveredNodeRef = useRef<SimNode | null>(null);
  const selectedNodeRef = useRef<SimNode | null>(null);
  const viewRef = useRef<ViewTransform>({ scale: 1, offsetX: 0, offsetY: 0 });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [view, setView] = useState<ViewTransform>({ scale: 1, offsetX: 0, offsetY: 0 });
  const navigate = useNavigate();

  function commitView(nextView: ViewTransform) {
    const normalized = {
      scale: Math.min(2.6, Math.max(0.38, nextView.scale)),
      offsetX: nextView.offsetX,
      offsetY: nextView.offsetY,
    };
    viewRef.current = normalized;
    setView(normalized);
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const activeCanvas = canvas;
    let frame = 0;
    let width = 1;
    let height = 1;

    function resize() {
      const rect = activeCanvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      width = Math.max(320, rect.width);
      height = Math.max(460, rect.height);
      activeCanvas.width = Math.floor(width * dpr);
      activeCanvas.height = Math.floor(height * dpr);
    }

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(activeCanvas);
    nodesRef.current = graph.nodes.map((node) => {
      const angle = hashNumber(node.id) * Math.PI * 2;
      const radius = initialRadius(node.type, width, height) * (0.72 + hashNumber(`${node.id}:r`) * 0.56);
      return {
        ...node,
        x: width / 2 + Math.cos(angle) * radius,
        y: height / 2 + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
      };
    });
    warmImageCache(nodesRef.current, imageCacheRef.current);

    function animate() {
      const iterations = nodesRef.current.length > 360 ? 1 : 2;
      for (let index = 0; index < iterations; index += 1) tick(nodesRef.current, graph.edges, width, height);
      drawGraph({
        canvas: activeCanvas,
        nodes: nodesRef.current,
        edges: graph.edges,
        imageCache: imageCacheRef.current,
        hoveredId: hoveredNodeRef.current?.id,
        selectedId: selectedNodeRef.current?.id,
        time: performance.now(),
        view: viewRef.current,
      });
      frame = window.requestAnimationFrame(animate);
    }
    animate();

    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frame);
    };
  }, [graph]);

  function updateSelectedNode(node: SimNode | null) {
    selectedNodeRef.current = node;
    setSelectedNode(node);
  }

  function updateHoveredNode(node: SimNode | null) {
    if (hoveredNodeRef.current?.id === node?.id) return;
    hoveredNodeRef.current = node;
    setHoveredNode(node);
  }

  function findNodeAt(clientX: number, clientY: number) {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const point = screenToWorld(clientX - rect.left, clientY - rect.top);
    return (
      nodesRef.current.find(
        (node) => Math.hypot(node.x - point.x, node.y - point.y) <= node.size + 12 / viewRef.current.scale,
      ) ?? null
    );
  }

  function pointFromEvent(event: ReactPointerEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    return screenToWorld(event.clientX - rect.left, event.clientY - rect.top);
  }

  function screenToWorld(x: number, y: number) {
    const current = viewRef.current;
    return {
      x: (x - current.offsetX) / current.scale,
      y: (y - current.offsetY) / current.scale,
    };
  }

  function zoomAt(clientX: number, clientY: number, nextScale: number) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const screenX = clientX - rect.left;
    const screenY = clientY - rect.top;
    const current = viewRef.current;
    const scale = Math.min(2.6, Math.max(0.38, nextScale));
    const worldX = (screenX - current.offsetX) / current.scale;
    const worldY = (screenY - current.offsetY) / current.scale;
    commitView({
      scale,
      offsetX: screenX - worldX * scale,
      offsetY: screenY - worldY * scale,
    });
  }

  function fitView() {
    const canvas = canvasRef.current;
    if (!canvas || nodesRef.current.length === 0) return;
    const rect = canvas.getBoundingClientRect();
    const minX = Math.min(...nodesRef.current.map((node) => node.x - node.size * 2));
    const maxX = Math.max(...nodesRef.current.map((node) => node.x + node.size * 2));
    const minY = Math.min(...nodesRef.current.map((node) => node.y - node.size * 2));
    const maxY = Math.max(...nodesRef.current.map((node) => node.y + node.size * 2));
    const graphWidth = Math.max(1, maxX - minX);
    const graphHeight = Math.max(1, maxY - minY);
    const scale = Math.min(
      1.45,
      Math.max(0.42, Math.min((rect.width - 80) / graphWidth, (rect.height - 80) / graphHeight)),
    );
    commitView({
      scale,
      offsetX: rect.width / 2 - (minX + graphWidth / 2) * scale,
      offsetY: rect.height / 2 - (minY + graphHeight / 2) * scale,
    });
  }

  const activeNode = selectedNode ?? hoveredNode;

  return (
    <div className="graph-stage">
      <canvas
        ref={canvasRef}
        className="h-full min-h-[calc(100svh-2rem)] w-full rounded-2xl"
        onDoubleClick={(event) => {
          const node = findNodeAt(event.clientX, event.clientY);
          if (node?.href) void navigate(node.href);
        }}
        onPointerDown={(event) => {
          const node = findNodeAt(event.clientX, event.clientY);
          if (!node) {
            updateSelectedNode(null);
            event.currentTarget.setPointerCapture(event.pointerId);
            panRef.current = {
              startX: event.clientX,
              startY: event.clientY,
              offsetX: viewRef.current.offsetX,
              offsetY: viewRef.current.offsetY,
            };
            return;
          }
          event.currentTarget.setPointerCapture(event.pointerId);
          node.pinned = true;
          node.vx = 0;
          node.vy = 0;
          const point = pointFromEvent(event);
          dragRef.current = { node, startX: point.x, startY: point.y, moved: false };
          updateSelectedNode(node);
        }}
        onPointerLeave={() => {
          updateHoveredNode(null);
        }}
        onPointerMove={(event) => {
          const drag = dragRef.current;
          const pan = panRef.current;
          if (pan) {
            commitView({
              ...viewRef.current,
              offsetX: pan.offsetX + event.clientX - pan.startX,
              offsetY: pan.offsetY + event.clientY - pan.startY,
            });
            updateHoveredNode(null);
            return;
          }
          const point = pointFromEvent(event);
          if (drag) {
            drag.node.x = point.x;
            drag.node.y = point.y;
            drag.node.vx = 0;
            drag.node.vy = 0;
            drag.moved ||= Math.hypot(point.x - drag.startX, point.y - drag.startY) > 5;
            updateHoveredNode(drag.node);
            return;
          }
          updateHoveredNode(findNodeAt(event.clientX, event.clientY));
        }}
        onPointerUp={(event) => {
          if (panRef.current) {
            event.currentTarget.releasePointerCapture(event.pointerId);
            panRef.current = null;
            return;
          }
          const drag = dragRef.current;
          if (!drag) return;
          event.currentTarget.releasePointerCapture(event.pointerId);
          drag.node.pinned = false;
          drag.node.vx = 0;
          drag.node.vy = 0;
          updateSelectedNode(drag.node);
          dragRef.current = null;
        }}
        onPointerCancel={() => {
          if (dragRef.current) dragRef.current.node.pinned = false;
          dragRef.current = null;
          panRef.current = null;
        }}
        onWheel={(event) => {
          event.preventDefault();
          const delta = event.deltaY > 0 ? 0.88 : 1.14;
          zoomAt(event.clientX, event.clientY, viewRef.current.scale * delta);
        }}
      />
      <div className="graph-toolbar">
        <Button
          aria-label={t('graph.zoomOut')}
          size="icon"
          type="button"
          variant="secondary"
          onClick={() => zoomAt(window.innerWidth / 2, window.innerHeight / 2, view.scale / 1.18)}
        >
          <Minus className="size-4" />
        </Button>
        <span>{Math.round(view.scale * 100)}%</span>
        <Button
          aria-label={t('graph.zoomIn')}
          size="icon"
          type="button"
          variant="secondary"
          onClick={() => zoomAt(window.innerWidth / 2, window.innerHeight / 2, view.scale * 1.18)}
        >
          <Plus className="size-4" />
        </Button>
        <Button aria-label={t('graph.fit')} size="icon" type="button" variant="secondary" onClick={fitView}>
          <Maximize2 className="size-4" />
        </Button>
        <Button
          aria-label={t('graph.reset')}
          size="icon"
          type="button"
          variant="secondary"
          onClick={() => commitView({ scale: 1, offsetX: 0, offsetY: 0 })}
        >
          <RotateCcw className="size-4" />
        </Button>
      </div>
      {activeNode ? (
        <div className="graph-inspector">
          <div className="graph-inspector-media" style={{ color: nodeColors[activeNode.type] }}>
            {activeNode.image ? (
              <img alt="" src={activeNode.image} />
            ) : (
              <div className="graph-inspector-orb" style={{ background: nodeColors[activeNode.type] }} />
            )}
          </div>
          <div className="graph-inspector-main">
            <span>{t(graphNodeLabelKeys[activeNode.type])}</span>
            <strong>{activeNode.label}</strong>
            {activeNode.subtitle ? <p>{activeNode.subtitle}</p> : null}
            {activeNode.details?.length ? (
              <div className="graph-inspector-details">
                {activeNode.details.slice(0, 6).map((detail) => (
                  <small key={detail}>{detail}</small>
                ))}
              </div>
            ) : null}
          </div>
          {activeNode.href ? (
            <Button asChild className="graph-inspector-action" size="sm" variant="secondary">
              <Link to={activeNode.href}>{t('graph.openSubject')}</Link>
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function SubjectGraphPage() {
  const { t } = useI18n();
  const params = useParams<{ subjectId: UUID }>();
  const subjectId = params.subjectId ?? '';
  const [mode, setMode] = useState<GraphMode>('balanced');
  const [sections, setSections] = useState<GraphSections>(defaultGraphSections);
  const subjectQuery = useQuery({ ...subjectQueries.detail(subjectId), enabled: Boolean(subjectId) });
  const graphPayloadQuery = useQuery({
    queryKey: [...subjectQueries.detail(subjectId).queryKey, 'graph-payload', mode, sections],
    queryFn: () => loadGraphPayload(subjectId, mode, sections),
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
  }, [
    graphPayloadQuery.data?.characters,
    graphPayloadQuery.data?.episodes,
    graphPayloadQuery.data?.relations,
    graphPayloadQuery.data?.staff,
    sections,
    subject,
    t,
  ]);

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
    <section className="graph-fullscreen">
      <Seo
        title={`${subjectTitle(subject, t('subject.title'))} · ${t('graph.title')}`}
        description={subject?.description_excerpt || subject?.summary || t('graph.description')}
        image={subject?.images?.poster || subject?.image || subject?.image_thumbnail}
        path={subjectId ? routes.subjectGraph(subjectId) : undefined}
      />
      <div className="graph-back">
        <Button asChild aria-label={t('common.back')} size="icon" variant="secondary">
          <Link to={subjectId ? routes.subject(subjectId) : routes.search}>
            <ArrowLeft className="size-4" />
          </Link>
        </Button>
      </div>
      <div className="graph-data-controls">
        <div className="graph-control-block">
          <span className="graph-control-label">{t('graph.mode')}</span>
          <div className="graph-mode-switch">
            {(['balanced', 'complete'] as const).map((value) => (
              <button
                className={mode === value ? 'is-active' : ''}
                key={value}
                type="button"
                onClick={() => setMode(value)}
              >
                {t(value === 'balanced' ? 'graph.modeBalanced' : 'graph.modeComplete')}
              </button>
            ))}
          </div>
        </div>
        <div className="graph-control-block graph-control-block-wide">
          <span className="graph-control-label">{t('graph.layers')}</span>
          <div className="graph-section-toggles">
            {graphSectionKeys.map((key) => (
              <button
                className={sections[key] ? 'is-active' : ''}
                key={key}
                type="button"
                onClick={() => setSections((current) => ({ ...current, [key]: !current[key] }))}
              >
                <span>{t(graphSectionLabelKeys[key])}</span>
                <small>{layerCounts[key]}</small>
              </button>
            ))}
          </div>
        </div>
        <div className="graph-control-stats">
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
