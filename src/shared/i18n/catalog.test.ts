import { describe, expect, it } from 'vitest';
import { locales, messages } from './catalog';

describe('translation catalogs', () => {
  it('contain the same keys for every locale', () => {
    const expectedKeys = Object.keys(messages['zh-CN']).sort();

    for (const locale of locales) {
      expect(Object.keys(messages[locale]).sort()).toEqual(expectedKeys);
    }
  });
});
