import { describe, expect, it } from 'vitest';
import type { GraphData } from './graph';
import { createGraphSimulation } from './simulation';

const graph: GraphData = {
  nodes: [
    { id: 'subject:1', label: 'Subject', type: 'subject', size: 46 },
    { id: 'character:1', label: 'Character', type: 'character', size: 20 },
  ],
  edges: [{ source: 'subject:1', target: 'character:1', label: 'character', strength: 0.9 }],
};

describe('graph simulation', () => {
  it('creates deterministic finite positions and advances with d3 forces', () => {
    const layout = createGraphSimulation(graph, 800, 600);
    const initialPositions = layout.nodes.map(({ x, y }) => ({ x, y }));

    layout.simulation.tick(20);

    expect(layout.nodes).toHaveLength(2);
    expect(layout.nodes.every((node) => Number.isFinite(node.x) && Number.isFinite(node.y))).toBe(true);
    expect(layout.nodes.map(({ x, y }) => ({ x, y }))).not.toEqual(initialPositions);
    layout.simulation.stop();
  });

  it('reheats a stopped simulation when the viewport changes', () => {
    const layout = createGraphSimulation(graph, 800, 600);
    layout.simulation.alpha(0);

    layout.resize(400, 700);

    expect(layout.simulation.alpha()).toBeCloseTo(0.35);
    layout.simulation.stop();
  });
});
