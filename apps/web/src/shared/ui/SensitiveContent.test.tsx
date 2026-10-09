import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { SensitiveContent } from './SensitiveContent';

describe('SensitiveContent', () => {
  it('does not expose concealed content before an explicit reveal', () => {
    const markup = renderToStaticMarkup(
      <SensitiveContent id="sensitive-body" isSensitive revealLabel="Reveal spoiler">
        <strong>Hidden body</strong>
      </SensitiveContent>,
    );

    expect(markup).not.toContain('Hidden body');
    expect(markup).toContain('aria-controls="sensitive-body"');
    expect(markup).toContain('aria-expanded="false"');
  });

  it('renders ordinary content without a reveal control', () => {
    const markup = renderToStaticMarkup(
      <SensitiveContent isSensitive={false} revealLabel="Reveal spoiler">
        <strong>Visible body</strong>
      </SensitiveContent>,
    );

    expect(markup).toContain('Visible body');
    expect(markup).not.toContain('<button');
  });
});
