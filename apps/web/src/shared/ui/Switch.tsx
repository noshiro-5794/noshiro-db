import type { ComponentProps } from 'react';
import { Switch as BaseSwitch } from '@base-ui/react/switch';
import { cn } from '@/shared/lib/cn';

function Switch({ className, ...props }: ComponentProps<typeof BaseSwitch.Root>) {
  return (
    <BaseSwitch.Root
      className={cn(
        'relative inline-flex h-5 w-9 shrink-0 cursor-default rounded-full border border-control-border bg-muted p-0.5 outline-none transition-[background-color,border-color,box-shadow] duration-[var(--ui-transition-fast)] data-[checked]:border-brand data-[checked]:bg-brand focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface data-[disabled]:cursor-not-allowed data-[disabled]:opacity-45',
        className,
      )}
      data-slot="switch"
      {...props}
    >
      <BaseSwitch.Thumb
        className="size-4 rounded-full bg-white shadow-[var(--ui-shadow-control)] transition-transform duration-[var(--ui-transition-fast)] data-[checked]:translate-x-4"
        data-slot="switch-thumb"
      />
    </BaseSwitch.Root>
  );
}

export { Switch };
