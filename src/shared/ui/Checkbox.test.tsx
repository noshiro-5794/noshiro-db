import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { CheckboxField } from './Checkbox';

describe('CheckboxField accessibility contract', () => {
  it('gives the checkbox an explicit accessible label', () => {
    const markup = renderToStaticMarkup(<CheckboxField checked>Mark as spoiler</CheckboxField>);
    const labelId = markup.match(/aria-labelledby="([^"]+)"/)?.[1];

    expect(labelId).toBeTruthy();
    expect(markup).toContain(`id="${labelId}"`);
    expect(markup).toContain('Mark as spoiler');
  });
});
