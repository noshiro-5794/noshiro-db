export const sessionSyncChannelName = 'noshiro-db:session';

export type SessionSyncMessage = { type: 'authenticated' | 'logout' };

export function isSessionSyncMessage(value: unknown): value is SessionSyncMessage {
  if (typeof value !== 'object' || value === null || !('type' in value)) return false;
  return value.type === 'authenticated' || value.type === 'logout';
}
