import { describe, expect, it } from 'vitest';
import { isSessionSyncMessage } from './session-sync';

describe('session sync messages', () => {
  it.each([{ type: 'authenticated' }, { type: 'logout' }])('accepts $type', (message) => {
    expect(isSessionSyncMessage(message)).toBe(true);
  });

  it.each([null, 'logout', {}, { type: 'refresh' }, { type: 1 }])('rejects invalid messages', (message) => {
    expect(isSessionSyncMessage(message)).toBe(false);
  });
});
