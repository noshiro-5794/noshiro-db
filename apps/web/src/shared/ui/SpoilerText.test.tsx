import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { SpoilerText } from './SpoilerText';

describe('SpoilerText', () => {
  it('conceals spoiler content behind an explicit accessible control', () => {
    const markup = renderToStaticMarkup(
      <SpoilerText id="spoiler-body" isSpoiler revealLabel="Reveal spoiler">
        Hidden content
      </SpoilerText>,
    );

    expect(markup).toContain('aria-hidden="true"');
    expect(markup).toContain('aria-controls="spoiler-body"');
    expect(markup).toContain('aria-expanded="false"');
    expect(markup).toContain('Reveal spoiler');
  });

  it('renders ordinary text without a reveal control', () => {
    const markup = renderToStaticMarkup(
      <SpoilerText isSpoiler={false} revealLabel="Reveal spoiler">
        Visible content
      </SpoilerText>,
    );

    expect(markup).toContain('Visible content');
    expect(markup).not.toContain('<button');
  });
});
