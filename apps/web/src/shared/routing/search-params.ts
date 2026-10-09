export function parseEnumParam<const Value extends string>(
  value: string | null | undefined,
  allowedValues: readonly Value[],
  fallback: Value,
): Value {
  return allowedValues.some((allowed) => allowed === value) ? (value as Value) : fallback;
}

export function parseIntegerParam(
  value: string | null | undefined,
  { min = Number.MIN_SAFE_INTEGER, max = Number.MAX_SAFE_INTEGER }: { min?: number; max?: number } = {},
) {
  if (!value || !/^-?\d+$/u.test(value)) return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= min && parsed <= max ? parsed : null;
}

export function parsePageParam(value: string | null | undefined, max = 10_000) {
  return parseIntegerParam(value, { min: 1, max }) ?? 1;
}

export function parseTextParam(
  value: string | null | undefined,
  { maxLength, trim = false }: { maxLength: number; trim?: boolean },
) {
  if (value === null || value === undefined) return '';
  const parsed = trim ? value.trim() : value;
  if (parsed.length > maxLength) return '';
  for (let index = 0; index < parsed.length; index += 1) {
    const code = parsed.charCodeAt(index);
    if (code <= 0x1f || code === 0x7f) return '';
  }
  return parsed;
}
