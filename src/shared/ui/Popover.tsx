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
          'z-50 w-72 rounded-xl border border-neutral-200 bg-white p-4 text-neutral-950 shadow-xl outline-none dark:border-neutral-800 dark:bg-neutral-950 dark:text-white',
          className,
        )}
        sideOffset={sideOffset}
        {...props}
      >
        {children}
        <PopoverPrimitive.Arrow className="fill-white dark:fill-neutral-950" height={8} width={14} />
      </PopoverPrimitive.Content>
    </PopoverPrimitive.Portal>
  );
}

export { Popover, PopoverContent, PopoverTrigger };
