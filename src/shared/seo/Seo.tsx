import { useEffect } from 'react';
import { useLocation } from '@tanstack/react-router';
import { env } from '@/shared/config/env';
import type { Locale } from '@/shared/i18n';
import { useI18n } from '@/shared/i18n';

const siteName = 'Noshiro DB';
const defaultTitle = siteName;
const defaultDescription =
  'Explore anime and galgames, browse weekly anime, and keep track of marks, reviews, and collections.';
const defaultImage = '/og-image.png';

const htmlLangByLocale: Record<Locale, string> = {
  'zh-CN': 'zh-CN',
  'en-US': 'en',
  'ja-JP': 'ja',
};

type SeoProps = {
  title?: string | undefined;
  description?: string | undefined;
  image?: string | null | undefined;
  path?: string | undefined;
  noindex?: boolean;
  type?: 'website' | 'article';
};

function absoluteUrl(value: string) {
  if (/^https?:\/\//u.test(value)) {
    return value;
  }
  return `${env.siteUrl}${value.startsWith('/') ? value : `/${value}`}`;
}

function ensureMeta(selector: string, attributes: Record<string, string>) {
  let element = document.head.querySelector<HTMLMetaElement>(selector);

  if (!element) {
    element = document.createElement('meta');
    document.head.appendChild(element);
  }

  Object.entries(attributes).forEach(([key, value]) => {
    element.setAttribute(key, value);
  });
}

function ensureCanonical(href: string) {
  let element = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');

  if (!element) {
    element = document.createElement('link');
    element.rel = 'canonical';
    document.head.appendChild(element);
  }

  element.href = href;
}

function compactDescription(value?: string) {
  return (value || defaultDescription).replace(/\s+/gu, ' ').trim().slice(0, 180);
}

export function Seo({ description, image, noindex = false, path, title, type = 'website' }: SeoProps) {
  const location = useLocation();
  const { locale } = useI18n();

  useEffect(() => {
    const resolvedTitle = title && title !== siteName ? `${title} | ${siteName}` : defaultTitle;
    const resolvedDescription = compactDescription(description);
    const resolvedUrl = absoluteUrl(path ?? `${location.pathname}${location.searchStr}`);
    const resolvedImage = absoluteUrl(image || defaultImage);

    document.documentElement.lang = htmlLangByLocale[locale];
    document.title = resolvedTitle;

    ensureCanonical(resolvedUrl);
    ensureMeta('meta[name="description"]', { name: 'description', content: resolvedDescription });
    ensureMeta('meta[name="robots"]', {
      name: 'robots',
      content: noindex ? 'noindex,nofollow' : 'index,follow',
    });
    ensureMeta('meta[property="og:site_name"]', { property: 'og:site_name', content: siteName });
    ensureMeta('meta[property="og:type"]', { property: 'og:type', content: type });
    ensureMeta('meta[property="og:title"]', { property: 'og:title', content: resolvedTitle });
    ensureMeta('meta[property="og:description"]', { property: 'og:description', content: resolvedDescription });
    ensureMeta('meta[property="og:url"]', { property: 'og:url', content: resolvedUrl });
    ensureMeta('meta[property="og:image"]', { property: 'og:image', content: resolvedImage });
    ensureMeta('meta[name="twitter:card"]', { name: 'twitter:card', content: 'summary_large_image' });
    ensureMeta('meta[name="twitter:title"]', { name: 'twitter:title', content: resolvedTitle });
    ensureMeta('meta[name="twitter:description"]', { name: 'twitter:description', content: resolvedDescription });
    ensureMeta('meta[name="twitter:image"]', { name: 'twitter:image', content: resolvedImage });
  }, [description, image, locale, location.pathname, location.searchStr, noindex, path, title, type]);

  return null;
}
