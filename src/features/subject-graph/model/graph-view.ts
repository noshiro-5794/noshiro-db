export type GraphView = {
  scale: number;
  offsetX: number;
  offsetY: number;
};

type PositionedNode = { x: number; y: number; size: number };

const minScale = 0.38;
const maxScale = 2.6;

function clampGraphScale(scale: number) {
  return Math.min(maxScale, Math.max(minScale, scale));
}

export function normalizeGraphView(view: GraphView): GraphView {
  return { ...view, scale: clampGraphScale(view.scale) };
}

export function graphScreenToWorld(view: GraphView, x: number, y: number) {
  return {
    x: (x - view.offsetX) / view.scale,
    y: (y - view.offsetY) / view.scale,
  };
}

export function zoomGraphViewAt(view: GraphView, screenX: number, screenY: number, nextScale: number): GraphView {
  const scale = clampGraphScale(nextScale);
  const world = graphScreenToWorld(view, screenX, screenY);
  return {
    scale,
    offsetX: screenX - world.x * scale,
    offsetY: screenY - world.y * scale,
  };
}

export function fitGraphView(nodes: PositionedNode[], width: number, height: number): GraphView | null {
  if (nodes.length === 0) return null;
  const minX = Math.min(...nodes.map((node) => node.x - node.size * 2));
  const maxX = Math.max(...nodes.map((node) => node.x + node.size * 2));
  const minY = Math.min(...nodes.map((node) => node.y - node.size * 2));
  const maxY = Math.max(...nodes.map((node) => node.y + node.size * 2));
  const graphWidth = Math.max(1, maxX - minX);
  const graphHeight = Math.max(1, maxY - minY);
  const scale = Math.min(1.45, Math.max(0.42, Math.min((width - 80) / graphWidth, (height - 80) / graphHeight)));
  return {
    scale,
    offsetX: width / 2 - (minX + graphWidth / 2) * scale,
    offsetY: height / 2 - (minY + graphHeight / 2) * scale,
  };
}
