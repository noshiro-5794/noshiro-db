import type { ComponentProps } from 'react';
import { Toggle as BaseToggle } from '@base-ui/react/toggle';
import {
  ToggleGroup as BaseToggleGroup,
  type ToggleGroupProps as BaseToggleGroupProps,
} from '@base-ui/react/toggle-group';
import { cn } from '@/shared/lib/cn';

type ToggleProps = Omit<ComponentProps<typeof BaseToggle>, 'className'> & {
  className?: string;
  variant?: 'default' | 'bare' | 'tab';
};

function Toggle({ className, variant = 'default', ...props }: ToggleProps) {
  return (
    <BaseToggle
      className={cn(
        'inline-flex h-[var(--ui-control-height)] shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-sm px-2.5 text-[13px] font-medium text-muted-foreground outline-none transition-[color,background-color,border-color,box-shadow] duration-[var(--ui-transition-fast)] hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:pointer-events-none disabled:opacity-45',
        variant === 'default' &&
          'gap-2 border border-transparent hover:bg-muted data-[pressed]:border-control-border data-[pressed]:bg-elevated data-[pressed]:text-foreground data-[pressed]:shadow-[var(--ui-shadow-control)]',
        variant === 'bare' && 'hover:bg-muted data-[pressed]:bg-muted data-[pressed]:text-foreground',
        variant === 'tab' &&
          'h-9 rounded-none border-b-2 border-transparent px-3 hover:bg-muted data-[pressed]:border-[var(--ui-accent)] data-[pressed]:text-foreground',
        className,
      )}
      data-slot="toggle"
      {...props}
    />
  );
}

type ToggleGroupProps<TValue extends string> = Omit<BaseToggleGroupProps<TValue>, 'className'> & {
  className?: string;
  variant?: 'default' | 'bare' | 'tab';
};

function ToggleGroup<TValue extends string>({ className, variant = 'default', ...props }: ToggleGroupProps<TValue>) {
  return (
    <BaseToggleGroup
      className={cn(
        'inline-flex items-center',
        variant === 'default' && 'gap-0.5 rounded-sm border border-border bg-muted p-0.5',
        variant === 'tab' && 'gap-1 border-b border-border-subtle',
        className,
      )}
      data-slot="toggle-group"
      {...props}
    />
  );
}

export { Toggle, ToggleGroup };
