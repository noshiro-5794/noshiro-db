import { describe, expect, it } from 'vitest';
import { plainText } from './text';

describe('plainText', () => {
  it('turns markup into the text around it', () => {
    expect(plainText('A <i>quiet</i> shelf')).toBe('A quiet shelf');
  });

  it('keeps a paragraph break where a provider put one', () => {
    expect(plainText('First line.<br><br>\nSecond line.')).toBe('First line.\n\nSecond line.');
  });

  it('decodes the character references providers escape', () => {
    expect(plainText('Rabbit &amp; bear &#39;friends&#39;')).toBe("Rabbit & bear 'friends'");
  });

  it('collapses runs of whitespace without eating the line breaks', () => {
    expect(plainText('  a\r\n\n\n   b  ')).toBe('a\n\nb');
  });

  it('leaves a comparison sign alone', () => {
    expect(plainText('Episode 3 > Episode 2')).toBe('Episode 3 > Episode 2');
  });
});
