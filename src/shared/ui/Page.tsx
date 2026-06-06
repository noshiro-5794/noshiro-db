import type { ReactNode } from 'react';
import { Seo } from '@/shared/seo/Seo';

type PageProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: ReactNode;
  hideHeader?: boolean;
  seo?: boolean;
  children?: ReactNode;
};

export function Page({ title, eyebrow, description, actions, hideHeader = false, seo = true, children }: PageProps) {
  return (
    <section className="page-shell">
      {seo ? <Seo title={title} description={description} /> : null}
      {hideHeader ? (
        <h1 className="sr-only">{title}</h1>
      ) : (
        <header className="page-header">
          <div className="page-header-inner">
            <div className="page-heading">
              {eyebrow ? <span className="page-eyebrow">{eyebrow}</span> : null}
              <h1 className="page-title">{title}</h1>
              {description ? <p className="page-description">{description}</p> : null}
            </div>
            {actions ? <div className="page-actions">{actions}</div> : null}
          </div>
        </header>
      )}
      <div className="page-content">{children}</div>
    </section>
  );
}
