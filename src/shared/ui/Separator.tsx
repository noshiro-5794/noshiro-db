import * as React from 'react';
import { cn } from '@/shared/lib/cn';

function Separator({
  className,
  orientation = 'horizontal',
  ...props
}: React.ComponentProps<'div'> & { orientation?: 'horizontal' | 'vertical' }) {
  return (
    <div
      aria-orientation={orientation}
      className={cn(
        'shrink-0 bg-neutral-200 dark:bg-neutral-800',
        orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
        className,
      )}
      role="separator"
      {...props}
    />
  );
}

export { Separator };
