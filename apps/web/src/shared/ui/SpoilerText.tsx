import { useId, useState, type ComponentProps } from 'react';
import { Eye } from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import { Button } from '@/shared/ui/Button';

type SpoilerTextProps = ComponentProps<'p'> & {
  isSpoiler: boolean;
  revealLabel: string;
};

export function SpoilerText({ children, className, isSpoiler, revealLabel, ...props }: SpoilerTextProps) {
  const generatedId = useId();
  const [revealed, setRevealed] = useState(false);
  const contentId = props.id ?? generatedId;

  if (!isSpoiler || revealed) {
    return (
      <p className={className} {...props} id={contentId}>
        {children}
      </p>
    );
  }

  return (
    <div
      className="relative min-h-12 overflow-hidden rounded-sm border border-border-subtle bg-muted"
      data-slot="spoiler-text"
    >
      <p aria-hidden="true" className={cn(className, 'invisible')} {...props} id={contentId}>
        {children}
      </p>
      <div className="absolute inset-0 grid place-items-center p-2">
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
    </div>
  );
}
