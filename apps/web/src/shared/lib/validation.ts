import type { UUID } from '@/shared/api';

const canonicalUuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/iu;

export function parseUuid(value: string | null | undefined): UUID | null {
  return value && canonicalUuidPattern.test(value) ? value.toLowerCase() : null;
}
