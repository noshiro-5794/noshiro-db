import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { FilterMenu } from './FilterMenu';

const options = [
  { label: 'All', value: '' },
  { label: 'Anime', value: 'anime' },
];

describe('FilterMenu', () => {
  it('names the field and the chosen value once the filter is narrowed', () => {
    const markup = renderToStaticMarkup(
      <FilterMenu label="Type" options={options} value="anime" onChange={() => undefined} />,
    );

    expect(markup).toContain('aria-label="Type: Anime"');
    expect(markup).toContain('data-slot="filter-trigger-value"');
  });

  it('shows the field name alone while the filter narrows nothing', () => {
    const markup = renderToStaticMarkup(
      <FilterMenu label="Type" options={options} value="" onChange={() => undefined} />,
    );

    expect(markup).toContain('aria-label="Type"');
    expect(markup).not.toContain('data-slot="filter-trigger-value"');
  });

  it('treats a non-empty option as the unset state when told which one it is', () => {
    const markup = renderToStaticMarkup(
      <FilterMenu
        emptyValue="all"
        label="Activity type"
        options={[
          { label: 'All activity', value: 'all' },
          { label: 'Posts', value: 'post_created' },
        ]}
        value="all"
        onChange={() => undefined}
      />,
    );

    expect(markup).toContain('aria-label="Activity type"');
    expect(markup).not.toContain('data-slot="filter-trigger-value"');
  });
});
