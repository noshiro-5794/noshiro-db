import type { Locale } from '@/shared/i18n';
import { enUSPages } from './en-US';
import { jaJPPages } from './ja-JP';
import { docsSlugs, type DocsPages, type DocsSlug } from './types';
import { zhCNPages } from './zh-CN';

export { defaultDocsSlug, docsSlugs, personalDocsSlug } from './types';

export function isDocsSlug(value: string): value is DocsSlug {
  return docsSlugs.some((slug) => slug === value);
}

export const docsContent: Record<Locale, DocsPages> = {
  'zh-CN': zhCNPages,
  'en-US': enUSPages,
  'ja-JP': jaJPPages,
};
