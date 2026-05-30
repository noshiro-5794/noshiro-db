import type { ReactNode } from 'react';

type PageProps = {
  title: string;
  children?: ReactNode;
};

export function Page({ title, children }: PageProps) {
  return (
    <section className="page">
      <h1>{title}</h1>
      {children}
    </section>
  );
}
