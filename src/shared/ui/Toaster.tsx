import { Toaster as Sonner, type ToasterProps } from 'sonner';

function Toaster(props: ToasterProps) {
  return (
    <Sonner
      closeButton
      position="top-center"
      toastOptions={{
        classNames: {
          toast: 'rounded-xl border border-neutral-200 bg-white text-neutral-950 shadow-xl dark:border-neutral-800 dark:bg-neutral-950 dark:text-white',
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
