import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { StarRatingControl } from './RatingStars';

describe('StarRatingControl', () => {
  it('exposes one selected score with a named control group', () => {
    const markup = renderToStaticMarkup(
      <StarRatingControl clearLabel="Clear" label="Simple rating" value="3" onChange={() => undefined} />,
    );

    expect(markup).toContain('role="group"');
    expect(markup).toContain('aria-label="Simple rating"');
    expect(markup).toContain('aria-label="Simple rating 3 / 5"');
    expect(markup.match(/aria-pressed="true"/g)).toHaveLength(1);
  });
});
