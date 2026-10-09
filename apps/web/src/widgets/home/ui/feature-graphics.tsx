import { Search, Star } from 'lucide-react';

/**
 * Small product graphics for the landing feature grid.
 *
 * dub draws one illustration per feature; these are the same idea with the
 * app's own surfaces instead of artwork, so they stay in step with the real
 * interface and need no assets.
 */
export function SearchGraphic() {
  return (
    <div className="grid gap-2">
      <div className="flex items-center gap-2 rounded-[var(--ui-radius-control)] border border-[var(--ui-border)] bg-[var(--ui-bg-elevated)] px-2.5 py-2">
        <Search className="size-3.5 shrink-0 text-[var(--ui-text-subtle)]" />
        <span className="truncate text-[12px] text-[var(--ui-text)]">SPY×FAMILY</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <span className="rounded-[4px] bg-[var(--ui-accent-soft)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--ui-accent-text)]">
          SPY×FAMILY
        </span>
        <span className="rounded-[4px] bg-[var(--ui-bg-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--ui-text-muted)]">
          スパイファミリー
        </span>
        <span className="rounded-[4px] bg-[var(--ui-bg-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--ui-text-muted)]">
          间谍过家家
        </span>
      </div>
    </div>
  );
}

export function ScheduleGraphic() {
  return (
    <div className="grid gap-2">
      <div className="flex items-end gap-1.5">
        {[38, 62, 46, 74, 52, 84, 44].map((height, index) => (
          <span
            className={
              index === 5
                ? 'w-full rounded-[3px] bg-[var(--ui-accent)]'
                : 'w-full rounded-[3px] bg-[var(--ui-bg-muted)]'
            }
            key={index}
            style={{ height: `${height * 0.6}px` }}
          />
        ))}
      </div>
      <span className="h-px w-full bg-[var(--ui-border-subtle)]" />
    </div>
  );
}

export function ProgressGraphic() {
  return (
    <div className="grid gap-2.5">
      <div className="flex items-center justify-between text-[10px] text-[var(--ui-text-muted)]">
        <span>EP 3 / 12</span>
        <span className="inline-flex items-center gap-1 text-[var(--ui-text)]">
          <Star className="size-3 fill-[var(--ui-warning)] text-[var(--ui-warning)]" />
          8.5
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[var(--ui-bg-muted)]">
        <span className="block h-full w-1/4 rounded-full bg-[var(--ui-accent)]" />
      </div>
      <div className="flex gap-1">
        {Array.from({ length: 12 }, (_, index) => (
          <span
            className={
              index < 3
                ? 'h-1 flex-1 rounded-full bg-[var(--ui-accent)]'
                : 'h-1 flex-1 rounded-full bg-[var(--ui-bg-muted)]'
            }
            key={index}
          />
        ))}
      </div>
    </div>
  );
}

export function CollectionGraphic() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex -space-x-6">
        {[0, 1, 2].map((index) => (
          <span
            className="h-16 w-11 rounded-[var(--ui-radius-control)] border border-[var(--ui-border)]"
            key={index}
            style={{
              background: `linear-gradient(150deg, color-mix(in srgb, var(--ui-accent) ${String(26 - index * 8)}%, var(--ui-bg-subtle)), var(--ui-bg-subtle))`,
            }}
          />
        ))}
      </div>
      <span className="rounded-[var(--ui-radius-pill)] border border-[var(--ui-border)] px-2 py-0.5 text-[10px] text-[var(--ui-text-muted)]">
        +12
      </span>
    </div>
  );
}
