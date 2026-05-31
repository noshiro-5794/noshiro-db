import type { ReactNode } from 'react';

type PageProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: ReactNode;
  children?: ReactNode;
};

export function Page({ title, eyebrow, description, actions, children }: PageProps) {
  return (
    <section className="flex min-h-full flex-col">
      <header className="border-b border-neutral-200 dark:border-neutral-800">
        <div className="mx-auto flex min-h-16 w-full max-w-6xl items-center justify-between gap-4 px-5 py-3">
          <div className="min-w-0">
            {eyebrow ? (
              <span className="block text-xs font-semibold uppercase text-neutral-500 dark:text-neutral-400">
                {eyebrow}
              </span>
            ) : null}
            <h1 className="truncate text-lg font-semibold leading-7 text-neutral-950 dark:text-neutral-50">{title}</h1>
            {description ? (
              <p className="mt-0.5 max-w-2xl truncate text-sm text-neutral-500 dark:text-neutral-400">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex flex-shrink-0 items-center gap-2">{actions}</div> : null}
        </div>
      </header>
      <div className="mx-auto w-full max-w-6xl flex-1 p-5">{children}</div>
    </section>
  );
}
