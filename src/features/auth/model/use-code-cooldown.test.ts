import { describe, expect, it } from 'vitest';
import { remainingCooldownSeconds } from './use-code-cooldown';

describe('remainingCooldownSeconds', () => {
  it('derives time from an absolute deadline without accumulating timer drift', () => {
    expect(remainingCooldownSeconds(61_000, 1_000)).toBe(60);
    expect(remainingCooldownSeconds(61_000, 20_501)).toBe(41);
    expect(remainingCooldownSeconds(61_000, 60_999)).toBe(1);
  });

  it('never returns a negative value after the deadline', () => {
    expect(remainingCooldownSeconds(1_000, 1_000)).toBe(0);
    expect(remainingCooldownSeconds(1_000, 20_000)).toBe(0);
  });
});
