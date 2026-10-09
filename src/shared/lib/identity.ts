/**
 * Stand-in artwork for people and works that have no picture.
 *
 * Instead of shipping a placeholder image, the app draws an initial on a
 * deterministic tone: the same account or work always gets the same colour, and
 * the tone is mixed against the current theme so it stays quiet in light and
 * dark mode alike.
 */
const fallbackTone = '#6d63a8'; // iris

const tones = [
  fallbackTone,
  '#3f6d9e', // azure
  '#2f7f73', // teal
  '#8a6a3b', // amber
  '#9c5560', // rose
  '#5b6b7f', // slate
];

function toneOf(seed: string) {
  let hash = 0;
  for (const character of seed) {
    hash = (hash * 31 + (character.codePointAt(0) ?? 0)) % 1_000_003;
  }
  return tones[hash % tones.length] ?? fallbackTone;
}

function mix(tone: string, weight: number, base: string) {
  return `color-mix(in srgb, ${tone} ${String(weight)}%, ${base})`;
}

/** Up to two initials: one glyph per word, or one glyph for a single word. */
export function initialsOf(name: string | null | undefined) {
  const words = (name ?? '').trim().split(/\s+/u).filter(Boolean);
  const glyphs = (words.length > 1 ? words.slice(0, 2) : words).map((word) => Array.from(word)[0] ?? '');
  return glyphs.join('').toLocaleUpperCase();
}

/** The first character of a title, used as the watermark on a missing cover. */
export function firstGlyphOf(text: string | null | undefined) {
  return Array.from((text ?? '').trim())[0] ?? '';
}

/** Background and ink for an avatar drawn from initials. */
export function avatarTone(seed: string | null | undefined) {
  const tone = toneOf((seed ?? '').trim() || '?');
  return {
    background: mix(tone, 18, 'var(--ui-bg-muted)'),
    color: mix(tone, 58, 'var(--ui-text)'),
  };
}

/** Background and ink for a catalogue cover that has no artwork yet. */
export function coverTone(seed: string | null | undefined) {
  const tone = toneOf((seed ?? '').trim() || '?');
  return {
    background: `linear-gradient(150deg, ${mix(tone, 30, 'var(--ui-bg-subtle)')}, ${mix(tone, 8, 'var(--ui-bg-subtle)')})`,
    color: mix(tone, 52, 'var(--ui-text-subtle)'),
  };
}
