const sessionCookieLockName = 'noshiro-db:session-cookie';

export async function withSessionCookieLock<T>(task: () => Promise<T>, signal?: AbortSignal | null) {
  if (typeof navigator === 'undefined' || !('locks' in navigator)) return task();

  return navigator.locks.request(
    sessionCookieLockName,
    {
      mode: 'exclusive',
      ...(signal ? { signal } : {}),
    },
    task,
  );
}
