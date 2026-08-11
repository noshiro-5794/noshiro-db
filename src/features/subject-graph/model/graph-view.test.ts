import { describe, expect, it } from 'vitest';
import { fitGraphView, graphScreenToWorld, normalizeGraphView, zoomGraphViewAt } from './graph-view';

describe('graph view transforms', () => {
  it('clamps scale and converts screen coordinates to world coordinates', () => {
    expect(normalizeGraphView({ scale: 10, offsetX: 4, offsetY: 6 }).scale).toBe(2.6);
    expect(graphScreenToWorld({ scale: 2, offsetX: 10, offsetY: 20 }, 30, 50)).toEqual({ x: 10, y: 15 });
  });

  it('keeps the world point under the cursor stable while zooming', () => {
    const current = { scale: 1, offsetX: 10, offsetY: 20 };
    const next = zoomGraphViewAt(current, 110, 120, 2);
    expect(graphScreenToWorld(next, 110, 120)).toEqual(graphScreenToWorld(current, 110, 120));
  });

  it('fits positioned nodes and returns null for an empty graph', () => {
    expect(fitGraphView([], 800, 600)).toBeNull();
    expect(fitGraphView([{ x: 100, y: 200, size: 20 }], 800, 600)).toMatchObject({
      scale: 1.45,
    });
  });
});
