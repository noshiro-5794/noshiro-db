import type { ComponentProps, ReactNode } from 'react';
import { Seo } from '@/shared/seo/Seo';

type AuthPageLayoutProps = {
  children: ReactNode;
  title: string;
};

type AuthFieldProps = ComponentProps<'input'> & {
  label: string;
  icon: ReactNode;
};

export function AuthPageLayout({ children, title }: AuthPageLayoutProps) {
  return (
    <main className="grid min-h-screen place-items-center bg-[var(--color-bg)] px-5 py-10 text-[var(--color-text)]">
      <Seo noindex title={title} />
      <div className="w-full max-w-[380px]">{children}</div>
    </main>
  );
}

export function AuthField({ icon, label, className, ...props }: AuthFieldProps) {
  return (
    <label className="grid gap-2">
      <span className="text-sm font-medium text-[var(--color-text)]">{label}</span>
      <span className="grid grid-cols-[20px_minmax(0,1fr)] items-center gap-3 rounded-xl bg-[var(--color-surface)] px-3 shadow-sm ring-1 ring-[var(--color-border)] transition focus-within:ring-4 focus-within:ring-[var(--color-focus-ring)]">
        <span className="text-neutral-400">{icon}</span>
        <input
          className={[
            'h-11 min-w-0 border-0 bg-transparent text-sm text-[var(--color-text)] outline-none placeholder:text-neutral-400',
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
