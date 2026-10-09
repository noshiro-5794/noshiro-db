import type { CSSProperties } from 'react';
import { Link } from '@tanstack/react-router';
import { Maximize2, Minus, Plus, RotateCcw } from 'lucide-react';
import { useI18n } from '@/shared/i18n';
import { resolvedRouteHref } from '@/shared/routing/resolved-href';
import { Button } from '@/shared/ui/Button';
import type { GraphNode } from '../model/graph';
import { graphNodeColors, graphNodeLabelKeys } from './graph-appearance';

export function GraphControls({
  scale,
  onFit,
  onReset,
  onZoomIn,
  onZoomOut,
}: {
  scale: number;
  onFit: () => void;
  onReset: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
}) {
  const { t } = useI18n();

  return (
    <div className="graph-toolbar" data-slot="graph-toolbar">
      <Button
        aria-label={t('graph.zoomOut')}
        size="icon"
        tooltip={t('graph.zoomOut')}
        type="button"
        variant="ghost"
        onClick={onZoomOut}
      >
        <Minus className="size-4" />
      </Button>
      <span className="graph-scale" data-slot="graph-scale">
        {Math.round(scale * 100)}%
      </span>
      <Button
        aria-label={t('graph.zoomIn')}
        size="icon"
        tooltip={t('graph.zoomIn')}
        type="button"
        variant="ghost"
        onClick={onZoomIn}
      >
        <Plus className="size-4" />
      </Button>
      <Button
        aria-label={t('graph.fit')}
        size="icon"
        tooltip={t('graph.fit')}
        type="button"
        variant="ghost"
        onClick={onFit}
      >
        <Maximize2 className="size-4" />
      </Button>
      <Button
        aria-label={t('graph.reset')}
        size="icon"
        tooltip={t('graph.reset')}
        type="button"
        variant="ghost"
        onClick={onReset}
      >
        <RotateCcw className="size-4" />
      </Button>
    </div>
  );
}

export function GraphInspector({ node }: { node: GraphNode | null }) {
  const { t } = useI18n();
  if (!node) return null;

  return (
    <div className="graph-inspector" data-slot="graph-inspector">
      <div className="graph-inspector-media" data-slot="graph-inspector-media">
        {node.image ? (
          <img alt="" decoding="async" loading="lazy" referrerPolicy="no-referrer" src={node.image} />
        ) : (
          <div
            aria-hidden="true"
            className="graph-inspector-swatch"
            style={{ background: graphNodeColors[node.type] }}
          />
        )}
      </div>
      <div className="graph-inspector-main" data-slot="graph-inspector-content">
        <span
          className="graph-inspector-kind"
          style={{ '--graph-node-color': graphNodeColors[node.type] } as CSSProperties}
        >
          {t(graphNodeLabelKeys[node.type])}
        </span>
        <strong className="graph-inspector-title">{node.label}</strong>
        {node.subtitle ? <p className="graph-inspector-description">{node.subtitle}</p> : null}
        {node.details?.length ? (
          <div className="graph-inspector-details" data-slot="graph-inspector-details">
            {node.details.slice(0, 6).map((detail) => (
              <small className="graph-inspector-detail" key={detail}>
                {detail}
              </small>
            ))}
          </div>
        ) : null}
      </div>
      {node.href ? (
        <Button asChild className="graph-inspector-action" size="sm" variant="secondary">
          <Link {...resolvedRouteHref(node.href)}>{t('graph.openSubject')}</Link>
        </Button>
      ) : null}
    </div>
  );
}
