import type { ComponentProps, ReactNode } from 'react';

type AuthPageLayoutProps = {
  children: ReactNode;
};

type AuthFieldProps = ComponentProps<'input'> & {
  label: string;
  icon: ReactNode;
};

export function AuthPageLayout({ children }: AuthPageLayoutProps) {
  return (
    <main className="grid min-h-screen place-items-center bg-neutral-50 px-5 py-10 text-neutral-950 dark:bg-neutral-950 dark:text-neutral-50">
      <div className="w-full max-w-[380px]">{children}</div>
    </main>
  );
}

export function AuthField({ icon, label, className, ...props }: AuthFieldProps) {
  return (
    <label className="grid gap-2">
      <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">{label}</span>
      <span className="grid grid-cols-[20px_minmax(0,1fr)] items-center gap-3 rounded-xl bg-white px-3 shadow-sm ring-1 ring-neutral-200 transition focus-within:ring-4 focus-within:ring-neutral-200 dark:bg-neutral-950 dark:ring-neutral-800 dark:focus-within:ring-neutral-800">
        <span className="text-neutral-400">{icon}</span>
        <input
          className={[
            'h-11 min-w-0 border-0 bg-transparent text-sm text-neutral-950 outline-none placeholder:text-neutral-400 dark:text-white',
            className,
          ]
            .filter(Boolean)
            .join(' ')}
          {...props}
        />
      </span>
    </label>
  );
}
