import { afterEach, describe, expect, it, vi } from 'vitest';
import { authApi } from '../api/session-api';
import { refreshAccessToken } from './session';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('refreshAccessToken', () => {
  it('shares an in-flight cookie rotation across Strict Mode effect replays', async () => {
    let resolveRefresh: ((value: { access: string }) => void) | undefined;
    const refreshRequest = new Promise<{ access: string }>((resolve) => {
      resolveRefresh = resolve;
    });
    const refreshSpy = vi.spyOn(authApi, 'refreshToken').mockReturnValue(refreshRequest);
    const firstController = new AbortController();

    const firstRefresh = refreshAccessToken({ signal: firstController.signal });
    firstController.abort();
    const replayedRefresh = refreshAccessToken();
    resolveRefresh?.({ access: 'rotated-access-token' });

    await expect(firstRefresh).resolves.toBe('rotated-access-token');
    await expect(replayedRefresh).resolves.toBe('rotated-access-token');
    expect(refreshSpy).toHaveBeenCalledOnce();
    expect(refreshSpy).toHaveBeenCalledWith();
  });

  it('does not start a cookie rotation for an already-aborted operation', () => {
    const refreshSpy = vi.spyOn(authApi, 'refreshToken');
    const controller = new AbortController();
    controller.abort();

    expect(() => refreshAccessToken({ signal: controller.signal })).toThrow();
    expect(refreshSpy).not.toHaveBeenCalled();
  });
});
