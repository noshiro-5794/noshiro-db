import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ResultsState } from './DataView';

const stateCopy = {
  emptyTitle: 'No results',
  errorTitle: 'Unable to load results',
  loadingTitle: 'Loading results',
};

describe('ResultsState', () => {
  it('renders an empty state without also rendering stale result content', () => {
    const markup = renderToStaticMarkup(
      <ResultsState {...stateCopy} status="empty">
        <span>stale result</span>
      </ResultsState>,
    );

    expect(markup).toContain('No results');
    expect(markup).not.toContain('stale result');
  });

  it('renders result content only when ready', () => {
    const markup = renderToStaticMarkup(
      <ResultsState {...stateCopy} status="ready">
        <span>current result</span>
      </ResultsState>,
    );

    expect(markup).toContain('current result');
    expect(markup).not.toContain('Loading results');
  });
});
