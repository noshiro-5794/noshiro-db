import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { CollectionCoverStack } from './CollectionCoverStack';

describe('CollectionCoverStack', () => {
  it('renders four stable cover layers', () => {
    const markup = renderToStaticMarkup(<CollectionCoverStack images={['/cover.jpg']} />);

    expect(markup).toContain('data-slot="collection-cover-stack"');
    expect(markup.match(/data-slot="collection-cover-layer"/gu)).toHaveLength(4);
    expect(markup).toContain('src="/cover.jpg"');
  });
});
