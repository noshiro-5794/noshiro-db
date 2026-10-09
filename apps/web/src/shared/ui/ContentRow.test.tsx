import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import {
  ContentRow,
  ContentRowActions,
  ContentRowExcerpt,
  ContentRowHeading,
  ContentRowMain,
  ContentRowMedia,
  ContentRowMeta,
  ContentRowTitle,
} from '@/shared/ui/ContentRow';

describe('ContentRow', () => {
  it('exposes stable composition slots', () => {
    const markup = renderToStaticMarkup(
      <ContentRow>
        <ContentRowMedia />
        <ContentRowMain>
          <ContentRowMeta>Meta</ContentRowMeta>
          <ContentRowHeading>
            <ContentRowTitle>Title</ContentRowTitle>
            <ContentRowActions>Actions</ContentRowActions>
          </ContentRowHeading>
          <ContentRowExcerpt>
            <p>Excerpt</p>
          </ContentRowExcerpt>
        </ContentRowMain>
      </ContentRow>,
    );

    for (const slot of [
      'content-row',
      'content-row-media',
      'content-row-main',
      'content-row-meta',
      'content-row-heading',
      'content-row-title',
      'content-row-actions',
      'content-row-excerpt',
    ]) {
      expect(markup).toContain(`data-slot="${slot}"`);
    }
  });
});
