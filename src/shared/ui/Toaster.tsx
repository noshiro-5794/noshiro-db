import { Toaster as Sonner, type ToasterProps } from 'sonner';

function Toaster(props: ToasterProps) {
  return (
    <Sonner
      closeButton
      position="top-center"
      toastOptions={{
        classNames: {
          toast:
            'rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] text-[var(--color-text)] shadow-[var(--shadow-hover)]',
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
