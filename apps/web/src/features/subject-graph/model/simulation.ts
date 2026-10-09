import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceRadial,
  forceSimulation,
  type Simulation,
  type SimulationLinkDatum,
} from 'd3-force';
import type { GraphData, GraphNode, GraphNodeType } from './graph';

export type GraphSimulationNode = GraphNode & {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number | null;
  fy?: number | null;
};

type GraphSimulationLink = SimulationLinkDatum<GraphSimulationNode> & {
  label: string;
  strength: number;
};

export type GraphSimulation = {
  nodes: GraphSimulationNode[];
  simulation: Simulation<GraphSimulationNode, GraphSimulationLink>;
  resize: (width: number, height: number) => void;
};

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

function createNodes(nodes: GraphNode[], width: number, height: number): GraphSimulationNode[] {
  return nodes.map((node) => {
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
}

export function createGraphSimulation(graph: GraphData, width: number, height: number): GraphSimulation {
  const nodes = createNodes(graph.nodes, width, height);
  const links: GraphSimulationLink[] = graph.edges.map((edge) => ({ ...edge }));
  const radialForce = forceRadial<GraphSimulationNode>(
    (node) => initialRadius(node.type, width, height),
    width / 2,
    height / 2,
  ).strength((node) => (node.type === 'subject' ? 0.9 : 0.075));
  const linkForce = forceLink<GraphSimulationNode, GraphSimulationLink>(links)
    .id((node) => node.id)
    .distance((link) => 92 + (link.strength < 0.7 ? 34 : 0))
    .strength((link) => Math.min(0.4, 0.08 + link.strength * 0.16));
  const simulation = forceSimulation<GraphSimulationNode>(nodes)
    .force(
      'charge',
      forceManyBody<GraphSimulationNode>()
        .strength((node) => (node.type === 'subject' ? -460 : node.type === 'meta' ? -55 : -110))
        .theta(0.9)
        .distanceMax(Math.max(width, height) * 0.9),
    )
    .force('link', linkForce)
    .force(
      'collision',
      forceCollide<GraphSimulationNode>()
        .radius((node) => node.size + 14)
        .strength(0.82),
    )
    .force('radial', radialForce)
    .alphaDecay(0.028)
    .velocityDecay(0.34)
    .stop();

  return {
    nodes,
    simulation,
    resize(nextWidth, nextHeight) {
      radialForce
        .radius((node) => initialRadius(node.type, nextWidth, nextHeight))
        .x(nextWidth / 2)
        .y(nextHeight / 2);
      simulation.alpha(0.35);
    },
  };
}
