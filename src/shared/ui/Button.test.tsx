import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { Button } from './Button';

describe('Button polymorphic rendering', () => {
  it('uses a string tooltip as the accessible name for every icon size', () => {
    for (const size of ['icon', 'icon-sm', 'icon-lg'] as const) {
      const markup = renderToStaticMarkup(
        <Button size={size} tooltip="Open settings">
          <span aria-hidden="true">x</span>
        </Button>,
      );

      expect(markup).toContain('aria-label="Open settings"');
    }
  });

  it('preserves anchor semantics when styling a navigation link', () => {
    const markup = renderToStaticMarkup(
      <Button asChild>
        <a href="/search">Search</a>
      </Button>,
    );

    expect(markup).toContain('<a href="/search"');
    expect(markup).not.toContain('role="button"');
  });

  it('prevents disabled child controls from being keyboard targets', () => {
    const markup = renderToStaticMarkup(
      <Button asChild disabled>
        <a href="/search">Search</a>
      </Button>,
    );

    expect(markup).toContain('aria-disabled="true"');
    expect(markup).toContain('tabindex="-1"');
  });
});
