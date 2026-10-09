import type { ReactElement, ReactNode } from 'react';
import { Tooltip as BaseTooltip } from '@base-ui/react/tooltip';
import { cn } from '@/shared/lib/cn';

const TooltipProvider = BaseTooltip.Provider;

type TooltipProps = {
  children: ReactElement;
  className?: string;
  content: ReactNode;
};

function Tooltip({ children, className, content }: TooltipProps) {
  return (
    <BaseTooltip.Root>
      <BaseTooltip.Trigger render={children} />
      <BaseTooltip.Portal>
        <BaseTooltip.Positioner className="z-50" sideOffset={6}>
          <BaseTooltip.Popup
            className={cn(
              'origin-[var(--transform-origin)] rounded-sm border border-border bg-elevated px-2 py-1 text-xs font-medium text-foreground shadow-[var(--ui-shadow-popup)] transition-[opacity,transform] duration-[var(--ui-transition-fast)] data-[ending-style]:scale-[0.985] data-[ending-style]:opacity-0 data-[starting-style]:scale-[0.985] data-[starting-style]:opacity-0',
              className,
            )}
            data-slot="tooltip"
          >
            {content}
          </BaseTooltip.Popup>
        </BaseTooltip.Positioner>
      </BaseTooltip.Portal>
    </BaseTooltip.Root>
  );
}

export { Tooltip, TooltipProvider };
