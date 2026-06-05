import type * as React from 'react';
import * as PopoverPrimitive from '@radix-ui/react-popover';
import { cn } from '@/lib/utils';

const Popover = PopoverPrimitive.Root;
const PopoverTrigger = PopoverPrimitive.Trigger;

function PopoverContent({
  align = 'center',
  children,
  className,
  sideOffset = 8,
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Content>) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        align={align}
        className={cn(
          'z-50 w-72 overflow-hidden rounded-2xl border border-[color-mix(in_srgb,var(--color-border)_82%,transparent)] bg-[color-mix(in_srgb,var(--color-surface-elevated)_94%,transparent)] p-4 text-[var(--color-text)] shadow-[var(--shadow-hover)] outline-none backdrop-blur-xl',
          className,
        )}
        collisionPadding={16}
        sideOffset={sideOffset}
        {...props}
      >
        {children}
        <PopoverPrimitive.Arrow className="fill-[var(--color-surface-elevated)]" height={8} width={14} />
      </PopoverPrimitive.Content>
    </PopoverPrimitive.Portal>
  );
}

export { Popover, PopoverContent, PopoverTrigger };
