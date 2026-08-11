import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { MarkdownRenderer } from './MarkdownRenderer';

function render(content: string) {
  return renderToStaticMarkup(<MarkdownRenderer content={content} />);
}

describe('MarkdownRenderer', () => {
  it('removes unsafe link protocols and ignores raw HTML', () => {
    const markup = render('[unsafe](javascript:alert(1))\n\n<script>alert(2)</script>');

    expect(markup).not.toContain('javascript:');
    expect(markup).not.toContain('<script');
    expect(markup).not.toContain('alert(2)');
  });

  it('isolates external links from the application window', () => {
    const markup = render('[external](https://example.com/path)');

    expect(markup).toContain('target="_blank"');
    expect(markup).toContain('rel="nofollow noopener noreferrer ugc"');
  });

  it('keeps internal links in the current window', () => {
    const markup = render('[internal](/subjects/1)');

    expect(markup).toContain('href="/subjects/1"');
    expect(markup).not.toContain('target="_blank"');
  });

  it('loads user-authored images without sending a referrer', () => {
    const markup = render('![cover](https://images.example/cover.jpg)');

    expect(markup).toContain('loading="lazy"');
    expect(markup).toContain('decoding="async"');
    expect(markup).toContain('referrerPolicy="no-referrer"');
  });

  it('keeps embedded document headings below the page title', () => {
    const markup = render('# Review heading\n\n## Section heading');

    expect(markup).not.toContain('<h1');
    expect(markup).toContain('<h2');
    expect(markup).toContain('Review heading</h2>');
    expect(markup).toContain('<h3');
    expect(markup).toContain('Section heading</h3>');
  });
});
