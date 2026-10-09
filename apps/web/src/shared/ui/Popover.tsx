import type { ComponentProps } from 'react';
import { Popover as BasePopover } from '@base-ui/react/popover';
import { cn } from '@/shared/lib/cn';

const Popover = BasePopover.Root;

function PopoverTrigger(props: ComponentProps<typeof BasePopover.Trigger>) {
  return <BasePopover.Trigger data-slot="popover-trigger" {...props} />;
}

type PopoverContentProps = ComponentProps<typeof BasePopover.Popup> &
  Pick<
    ComponentProps<typeof BasePopover.Positioner>,
    'align' | 'alignOffset' | 'collisionAvoidance' | 'side' | 'sideOffset'
  >;

function PopoverContent({
  align = 'center',
  alignOffset,
  children,
  className,
  collisionAvoidance,
  side = 'bottom',
  sideOffset = 6,
  ...props
}: PopoverContentProps) {
  return (
    <BasePopover.Portal>
      <BasePopover.Positioner
        align={align}
        alignOffset={alignOffset}
        className="z-50 outline-none"
        collisionAvoidance={collisionAvoidance}
        side={side}
        sideOffset={sideOffset}
      >
        <BasePopover.Popup
          className={cn(
            'w-72 origin-[var(--transform-origin)] overflow-hidden rounded-sm border border-border bg-elevated p-4 text-foreground shadow-[var(--ui-shadow-popup)] outline-none transition-[opacity,transform] duration-[var(--ui-transition-fast)] data-[ending-style]:scale-[0.985] data-[ending-style]:opacity-0 data-[starting-style]:scale-[0.985] data-[starting-style]:opacity-0',
            className,
          )}
          data-slot="popover-content"
          {...props}
        >
          {children}
        </BasePopover.Popup>
      </BasePopover.Positioner>
    </BasePopover.Portal>
  );
}

export { Popover, PopoverContent, PopoverTrigger };
