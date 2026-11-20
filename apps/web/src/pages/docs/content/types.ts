export const defaultDocsSlug = 'introduction';
export const personalDocsSlug = 'owner';

export const docsSlugs = [
  defaultDocsSlug,
  personalDocsSlug,
  'guide',
  'reviews',
  'community',
  'terms',
  'privacy',
  'security',
  'status',
] as const;

export type DocsSlug = (typeof docsSlugs)[number];

type DocsSection = {
  id: string;
  title: string;
  body: string[];
};

type DocsPage = {
  title: string;
  description: string;
  sections: DocsSection[];
};

export type DocsPages = Record<DocsSlug, DocsPage>;
