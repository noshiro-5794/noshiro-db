import { afterEach, describe, expect, it, vi } from 'vitest';
import { withSessionCookieLock } from './session-cookie-lock';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('withSessionCookieLock', () => {
  it('uses a browser-wide exclusive lock for session-cookie mutations', async () => {
    const controller = new AbortController();
    const task = vi.fn().mockResolvedValue('access-token');
    const request = vi.fn(
      async (_name: string, _options: LockOptions, callback: (lock: Lock | null) => Promise<unknown>) => callback(null),
    );
    vi.stubGlobal('navigator', { locks: { request } });

    await expect(withSessionCookieLock(task, controller.signal)).resolves.toBe('access-token');
    expect(request).toHaveBeenCalledWith(
      'noshiro-db:session-cookie',
      { mode: 'exclusive', signal: controller.signal },
      task,
    );
    expect(task).toHaveBeenCalledOnce();
  });

  it('runs directly when Web Locks is unavailable', async () => {
    const task = vi.fn().mockResolvedValue('access-token');
    vi.stubGlobal('navigator', {});

    await expect(withSessionCookieLock(task)).resolves.toBe('access-token');
    expect(task).toHaveBeenCalledOnce();
  });
});
