import { useEffect, useId, useRef, useState, type ComponentProps } from 'react';
import { Eye } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { Button } from '@/shared/ui/Button';

type SensitiveContentProps = ComponentProps<'div'> & {
  contentClassName?: string;
  contentLabel?: string;
  isSensitive: boolean;
  revealLabel: string;
};

function SensitiveContent({
  children,
  className,
  contentClassName,
  contentLabel,
  isSensitive,
  revealLabel,
  ...props
}: SensitiveContentProps) {
  const generatedId = useId();
  const [revealed, setRevealed] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const contentId = props.id ?? generatedId;

  useEffect(() => {
    if (revealed) contentRef.current?.focus();
  }, [revealed]);

  if (!isSensitive) {
    return (
      <div className={cn('min-w-0', className)} data-slot="sensitive-content">
        <div className={cn('min-w-0', contentClassName)} {...props} id={contentId}>
          {children}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('min-w-0', className)} data-revealed={revealed || undefined} data-slot="sensitive-content">
      <div
        aria-label={contentLabel ?? revealLabel}
        className={cn('min-w-0 outline-none', contentClassName)}
        hidden={!revealed}
        id={contentId}
        ref={contentRef}
        role="region"
        tabIndex={revealed ? -1 : undefined}
        {...props}
      >
        {revealed ? children : null}
      </div>
      {!revealed ? (
        <div className="grid min-h-28 place-items-center rounded-sm border border-border-subtle bg-muted p-4">
          <Button
            aria-controls={contentId}
            aria-expanded="false"
            size="sm"
            type="button"
            variant="secondary"
            onClick={() => {
              setRevealed(true);
            }}
          >
            <Eye className="size-4" />
            {revealLabel}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export { SensitiveContent };
