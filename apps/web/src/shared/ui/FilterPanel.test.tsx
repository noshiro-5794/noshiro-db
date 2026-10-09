import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { FilterPanel, FilterPanelHeader, FilterTag } from '@/shared/ui/FilterPanel';

describe('FilterPanel', () => {
  it('exposes panel and active tag slots', () => {
    const markup = renderToStaticMarkup(
      <FilterPanel>
        <FilterPanelHeader>Filters</FilterPanelHeader>
        <FilterTag active>Selected</FilterTag>
      </FilterPanel>,
    );

    expect(markup).toContain('data-slot="filter-panel"');
    expect(markup).toContain('data-slot="filter-panel-header"');
    expect(markup).toContain('data-slot="filter-tag"');
    expect(markup).toContain('data-active="true"');
  });
});
