import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { FilterMenu } from './FilterMenu';

describe('FilterMenu', () => {
  it('includes the selected option in the trigger name', () => {
    const markup = renderToStaticMarkup(
      <FilterMenu
        label="Sort"
        options={[
          { label: 'Newest', value: 'newest' },
          { label: 'Highest rating', value: 'rating' },
        ]}
        value="rating"
        onChange={() => undefined}
      />,
    );

    expect(markup).toContain('aria-label="Sort: Highest rating"');
  });
});
