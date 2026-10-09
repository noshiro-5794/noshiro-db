import type { GraphData, GraphNodeType } from './graph';

const maxRenderableGraphNodes = 900;

export function applyGraphDensityLimits(graph: GraphData): GraphData {
  return normalizeGraphDensity(limitGraphDensity(graph));
}

function limitGraphDensity(graph: GraphData): GraphData {
  if (graph.nodes.length <= maxRenderableGraphNodes) return graph;

  const priority: Record<GraphNodeType, number> = {
    subject: 0,
    relation: 1,
    character: 2,
    staff: 3,
    meta: 4,
    episode: 5,
  };
  const selectedNodes = graph.nodes
    .map((node, index) => ({ node, index }))
    .sort((a, b) => priority[a.node.type] - priority[b.node.type] || a.index - b.index)
    .slice(0, maxRenderableGraphNodes)
    .sort((a, b) => a.index - b.index)
    .map(({ node }) => node);
  const selectedNodeIds = new Set(selectedNodes.map((node) => node.id));

  return {
    nodes: selectedNodes,
    edges: graph.edges.filter((edge) => selectedNodeIds.has(edge.source) && selectedNodeIds.has(edge.target)),
    truncated: true,
  };
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
