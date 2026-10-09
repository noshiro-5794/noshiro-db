import type { GraphEdge } from '../model/graph';
import type { GraphSimulationNode } from '../model/simulation';
import { graphNodeColors } from './graph-appearance';

export type CachedGraphImage = {
  image: HTMLImageElement;
  ready: boolean;
};

export type GraphViewTransform = {
  scale: number;
  offsetX: number;
  offsetY: number;
};

export function drawGraph({
  canvas,
  edges,
  hoveredId,
  imageCache,
  nodeById,
  nodes,
  selectedId,
  view,
}: {
  canvas: HTMLCanvasElement;
  nodes: GraphSimulationNode[];
  edges: GraphEdge[];
  imageCache: Map<string, CachedGraphImage>;
  nodeById: ReadonlyMap<string, GraphSimulationNode>;
  hoveredId?: string | undefined;
  selectedId?: string | undefined;
  view: GraphViewTransform;
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

  context.fillStyle = '#101012';
  context.fillRect(0, 0, viewWidth, viewHeight);
  drawGrid(context, viewWidth, viewHeight);

  context.save();
  context.translate(view.offsetX, view.offsetY);
  context.scale(view.scale, view.scale);

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
    if (highlighted || node.fx != null || node.fy != null) {
      const color = graphNodeColors[node.type];
      context.strokeStyle = colorWithAlpha(color, highlighted ? 0.42 : 0.24);
      context.lineWidth = highlighted ? 2 : 1;
      context.beginPath();
      context.arc(node.x, node.y, node.size + 8, 0, Math.PI * 2);
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

function drawGrid(context: CanvasRenderingContext2D, width: number, height: number) {
  context.save();
  context.lineWidth = 1;
  context.strokeStyle = 'rgba(255,255,255,0.025)';
  context.beginPath();

  for (let x = 40.5; x < width; x += 40) {
    context.moveTo(x, 0);
    context.lineTo(x, height);
  }

  for (let y = 40.5; y < height; y += 40) {
    context.moveTo(0, y);
    context.lineTo(width, y);
  }

  context.stroke();
  context.restore();
}

function drawNode(
  context: CanvasRenderingContext2D,
  node: GraphSimulationNode,
  imageCache: Map<string, CachedGraphImage>,
  highlighted: boolean,
) {
  const color = graphNodeColors[node.type];
  const cached = node.image ? imageCache.get(node.image) : null;
  const image = cached?.ready ? cached.image : null;
  context.save();

  if (node.type === 'subject' || node.type === 'relation') {
    const width = node.type === 'subject' ? node.size * 1.36 : node.size * 1.28;
    const height = node.type === 'subject' ? node.size * 1.92 : node.size * 1.82;
    const x = node.x - width / 2;
    const y = node.y - height / 2;
    context.fillStyle = 'rgba(255,255,255,0.08)';
    context.beginPath();
    context.roundRect(x, y, width, height, 4);
    context.fill();
    context.clip();
    if (image) drawCoverImage(context, image, x, y, width, height);
    else {
      context.fillStyle = colorWithAlpha(color, 0.58);
      context.fillRect(x, y, width, height);
    }
    context.restore();
    context.save();
    context.strokeStyle = highlighted ? 'rgba(255,255,255,0.9)' : colorWithAlpha(color, 0.42);
    context.lineWidth = highlighted ? 2 : 1;
    context.beginPath();
    context.roundRect(x, y, width, height, 4);
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
    if (image) drawCoverImage(context, image, node.x - node.size, node.y - node.size, node.size * 2, node.size * 2);
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
    context.roundRect(node.x - width / 2, node.y - height / 2, width, height, 4);
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

export function syncGraphImageCache(nodes: GraphSimulationNode[], imageCache: Map<string, CachedGraphImage>) {
  const activeImages = new Set(nodes.flatMap((node) => (node.image ? [node.image] : [])));
  for (const [source, cached] of imageCache) {
    if (activeImages.has(source)) continue;
    releaseCachedImage(cached);
    imageCache.delete(source);
  }

  for (const node of nodes) {
    if (!node.image || imageCache.has(node.image)) continue;
    const image = new Image();
    const cached = { image, ready: false };
    image.decoding = 'async';
    image.referrerPolicy = 'no-referrer';
    image.onload = () => {
      cached.ready = true;
      image.onload = null;
      image.onerror = null;
    };
    image.onerror = () => {
      image.onload = null;
      image.onerror = null;
    };
    image.src = node.image;
    imageCache.set(node.image, cached);
  }
}

function releaseCachedImage(cached: CachedGraphImage) {
  cached.image.onload = null;
  cached.image.onerror = null;
  if (!cached.ready) cached.image.removeAttribute('src');
}

export function clearGraphImageCache(imageCache: Map<string, CachedGraphImage>) {
  for (const cached of imageCache.values()) releaseCachedImage(cached);
  imageCache.clear();
}

function colorWithAlpha(hex: string, alpha: number) {
  const value = hex.replace('#', '');
  const red = Number.parseInt(value.slice(0, 2), 16);
  const green = Number.parseInt(value.slice(2, 4), 16);
  const blue = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${red},${green},${blue},${alpha})`;
}
