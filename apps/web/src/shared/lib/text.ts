/** Paragraph-ish tag whose end is a line break rather than nothing. */
const BLOCK_BOUNDARY = /<br\s*\/?>|<\/(?:p|div|li|h[1-6]|blockquote|tr)\s*>/giu;
const TAG = /<[^>]*>/gu;
const CHARACTER_REFERENCE = /&(#[0-9]+|#x[0-9a-f]+|[a-z]+);/giu;

const NAMED_REFERENCES: Record<string, string> = {
  amp: '&',
  apos: "'",
  gt: '>',
  lt: '<',
  nbsp: ' ',
  quot: '"',
};

function decodeReferences(value: string): string {
  return value.replace(CHARACTER_REFERENCE, (match, reference: string) => {
    if (!reference.startsWith('#')) return NAMED_REFERENCES[reference.toLowerCase()] ?? match;
    const isHex = reference[1]?.toLowerCase() === 'x';
    const code = Number.parseInt(isHex ? reference.slice(2) : reference.slice(1), isHex ? 16 : 10);
    return Number.isSafeInteger(code) && code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : match;
  });
}

/**
 * Provider synopses arrive as small HTML fragments — `<br><br>` between
 * paragraphs, `<i>` for emphasis, escaped ampersands — and the catalogue keeps
 * them verbatim. Every surface renders a description as text, so the boundary
 * that decodes a provider payload is also the one that turns that markup into
 * the plain text those surfaces expect.
 */
export function plainText(value: string): string {
  return decodeReferences(value.replace(BLOCK_BOUNDARY, '\n').replace(TAG, ''))
    .replace(/[^\S\n]+/gu, ' ')
    .replace(/ *\n */gu, '\n')
    .replace(/\n{3,}/gu, '\n\n')
    .trim();
}
