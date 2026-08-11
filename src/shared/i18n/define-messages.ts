export const locales = ['zh-CN', 'en-US', 'ja-JP'] as const;

export type Locale = (typeof locales)[number];

type MessageMap = Record<string, string>;

export function defineMessages<
  const Chinese extends MessageMap,
  const English extends Record<keyof Chinese, string>,
  const Japanese extends Record<keyof Chinese, string>,
>(messages: {
  'zh-CN': Chinese;
  'en-US': English & Record<Exclude<keyof English, keyof Chinese>, never>;
  'ja-JP': Japanese & Record<Exclude<keyof Japanese, keyof Chinese>, never>;
}) {
  return messages;
}
