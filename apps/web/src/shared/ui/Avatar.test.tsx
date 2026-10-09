import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { Avatar } from './Avatar';

describe('Avatar', () => {
  it('keeps an accessible image name while the remote image is still loading', () => {
    const markup = renderToStaticMarkup(<Avatar alt="Noshiro" src="https://example.com/avatar.png" />);

    expect(markup).toContain('role="img"');
    expect(markup).toContain('aria-label="Noshiro"');
    expect(markup).toContain('aria-hidden="true"');
    expect(markup).toContain('data-slot="avatar-fallback"');
  });

  it('renders a stable fallback when no image is available', () => {
    const markup = renderToStaticMarkup(<Avatar />);

    expect(markup).toContain('data-slot="avatar-fallback"');
    expect(markup).not.toContain('<img');
  });
});
