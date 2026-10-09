import { useEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useI18n } from '@/shared/i18n';
import type { GraphData, GraphNode } from '../model/graph';
import {
  fitGraphView,
  graphScreenToWorld,
  normalizeGraphView,
  zoomGraphViewAt,
  type GraphView,
} from '../model/graph-view';
import { createGraphSimulation, type GraphSimulation, type GraphSimulationNode } from '../model/simulation';
import { clearGraphImageCache, drawGraph, syncGraphImageCache, type CachedGraphImage } from './graph-renderer';
import { GraphControls, GraphInspector } from './GraphOverlays';
import './graph.css';

type DragState = {
  node: GraphSimulationNode;
  startX: number;
  startY: number;
  moved: boolean;
};

type PanState = {
  startX: number;
  startY: number;
  offsetX: number;
  offsetY: number;
};

const initialView: GraphView = { scale: 1, offsetX: 0, offsetY: 0 };

export function GraphCanvas({ graph }: { graph: GraphData }) {
  const { t } = useI18n();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const nodesRef = useRef<GraphSimulationNode[]>([]);
  const imageCacheRef = useRef(new Map<string, CachedGraphImage>());
  const dragRef = useRef<DragState | null>(null);
  const panRef = useRef<PanState | null>(null);
  const hoveredNodeRef = useRef<GraphSimulationNode | null>(null);
  const selectedNodeRef = useRef<GraphSimulationNode | null>(null);
  const simulationFramesRef = useRef(0);
  const simulationRef = useRef<GraphSimulation | null>(null);
  const viewRef = useRef<GraphView>(initialView);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [view, setView] = useState<GraphView>(initialView);
  const navigate = useNavigate();

  useEffect(
    () => () => {
      clearGraphImageCache(imageCacheRef.current);
    },
    [],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const activeCanvas = canvas;

    let frame = 0;
    let width = 1;
    let height = 1;
    let layout: GraphSimulation | null = null;

    function resize() {
      const rect = activeCanvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      width = Math.max(320, rect.width);
      height = Math.max(460, rect.height);
      activeCanvas.width = Math.floor(width * dpr);
      activeCanvas.height = Math.floor(height * dpr);
      layout?.resize(width, height);
      simulationFramesRef.current = Math.max(simulationFramesRef.current, 120);
    }

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(activeCanvas);
    const graphSimulation = createGraphSimulation(graph, width, height);
    layout = graphSimulation;
    simulationRef.current = graphSimulation;
    nodesRef.current = graphSimulation.nodes;
    const nodeById = new Map(nodesRef.current.map((node) => [node.id, node]));
    syncGraphImageCache(nodesRef.current, imageCacheRef.current);
    simulationFramesRef.current = nodesRef.current.length > 360 ? 180 : 300;
    let lastDrawTime = 0;

    function animate(time: number) {
      frame = window.requestAnimationFrame(animate);
      const frameInterval = simulationFramesRef.current > 0 || dragRef.current ? 1000 / 30 : 1000 / 15;
      if (time - lastDrawTime < frameInterval) return;
      lastDrawTime = time;

      if (simulationFramesRef.current > 0) {
        graphSimulation.simulation.tick(nodesRef.current.length > 360 ? 1 : 2);
        simulationFramesRef.current -= 1;
      }
      drawGraph({
        canvas: activeCanvas,
        nodes: nodesRef.current,
        edges: graph.edges,
        imageCache: imageCacheRef.current,
        nodeById,
        hoveredId: hoveredNodeRef.current?.id,
        selectedId: selectedNodeRef.current?.id,
        view: viewRef.current,
      });
    }
    frame = window.requestAnimationFrame(animate);

    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frame);
      graphSimulation.simulation.stop();
      dragRef.current = null;
      panRef.current = null;
      if (simulationRef.current === graphSimulation) simulationRef.current = null;
    };
  }, [graph]);

  function commitView(nextView: GraphView) {
    const normalized = normalizeGraphView(nextView);
    viewRef.current = normalized;
    setView(normalized);
  }

  function updateSelectedNode(node: GraphSimulationNode | null) {
    selectedNodeRef.current = node;
    setSelectedNode(node);
  }

  function updateHoveredNode(node: GraphSimulationNode | null) {
    if (hoveredNodeRef.current?.id === node?.id) return;
    hoveredNodeRef.current = node;
    setHoveredNode(node);
  }

  function screenPoint(clientX: number, clientY: number) {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  }

  function worldPoint(clientX: number, clientY: number) {
    const point = screenPoint(clientX, clientY);
    return point ? graphScreenToWorld(viewRef.current, point.x, point.y) : { x: 0, y: 0 };
  }

  function findNodeAt(clientX: number, clientY: number) {
    const point = worldPoint(clientX, clientY);
    return (
      nodesRef.current.find(
        (node) => Math.hypot(node.x - point.x, node.y - point.y) <= node.size + 12 / viewRef.current.scale,
      ) ?? null
    );
  }

  function zoomAt(clientX: number, clientY: number, nextScale: number) {
    const point = screenPoint(clientX, clientY);
    if (!point) return;
    commitView(zoomGraphViewAt(viewRef.current, point.x, point.y, nextScale));
  }

  function zoomBy(factor: number) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, viewRef.current.scale * factor);
  }

  function fitView() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const nextView = fitGraphView(nodesRef.current, rect.width, rect.height);
    if (nextView) commitView(nextView);
  }

  function releasePointerCapture(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function releaseDraggedNode() {
    const drag = dragRef.current;
    if (!drag) return null;
    drag.node.fx = null;
    drag.node.fy = null;
    drag.node.vx = 0;
    drag.node.vy = 0;
    dragRef.current = null;
    return drag.node;
  }

  const activeNode = selectedNode ?? hoveredNode;

  return (
    <div className="graph-stage" data-slot="graph-stage">
      <canvas
        ref={canvasRef}
        aria-label={t('graph.title')}
        className="h-full w-full"
        data-slot="graph-canvas"
        onDoubleClick={(event) => {
          const node = findNodeAt(event.clientX, event.clientY);
          if (node?.href) void navigate({ href: node.href });
        }}
        onPointerDown={(event) => {
          const node = findNodeAt(event.clientX, event.clientY);
          event.currentTarget.setPointerCapture(event.pointerId);
          if (!node) {
            updateSelectedNode(null);
            panRef.current = {
              startX: event.clientX,
              startY: event.clientY,
              offsetX: viewRef.current.offsetX,
              offsetY: viewRef.current.offsetY,
            };
            return;
          }
          node.fx = node.x;
          node.fy = node.y;
          node.vx = 0;
          node.vy = 0;
          simulationRef.current?.simulation.alpha(0.35);
          simulationFramesRef.current = Math.max(simulationFramesRef.current, 90);
          const point = worldPoint(event.clientX, event.clientY);
          dragRef.current = { node, startX: point.x, startY: point.y, moved: false };
          updateSelectedNode(node);
        }}
        onPointerLeave={() => {
          updateHoveredNode(null);
        }}
        onPointerMove={(event) => {
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
          const drag = dragRef.current;
          const point = worldPoint(event.clientX, event.clientY);
          if (drag) {
            drag.node.x = point.x;
            drag.node.y = point.y;
            drag.node.fx = point.x;
            drag.node.fy = point.y;
            drag.node.vx = 0;
            drag.node.vy = 0;
            simulationRef.current?.simulation.alpha(0.35);
            simulationFramesRef.current = Math.max(simulationFramesRef.current, 90);
            drag.moved ||= Math.hypot(point.x - drag.startX, point.y - drag.startY) > 5;
            updateHoveredNode(drag.node);
            return;
          }
          updateHoveredNode(findNodeAt(event.clientX, event.clientY));
        }}
        onPointerUp={(event) => {
          releasePointerCapture(event);
          if (panRef.current) {
            panRef.current = null;
            return;
          }
          const node = releaseDraggedNode();
          if (!node) return;
          simulationRef.current?.simulation.alpha(0.3);
          simulationFramesRef.current = Math.max(simulationFramesRef.current, 120);
          updateSelectedNode(node);
        }}
        onPointerCancel={(event) => {
          releasePointerCapture(event);
          releaseDraggedNode();
          panRef.current = null;
        }}
        onWheel={(event) => {
          event.preventDefault();
          zoomAt(event.clientX, event.clientY, viewRef.current.scale * (event.deltaY > 0 ? 0.88 : 1.14));
        }}
      />
      <GraphControls
        scale={view.scale}
        onFit={fitView}
        onReset={() => {
          commitView(initialView);
        }}
        onZoomIn={() => {
          zoomBy(1.18);
        }}
        onZoomOut={() => {
          zoomBy(1 / 1.18);
        }}
      />
      <GraphInspector node={activeNode} />
    </div>
  );
}
