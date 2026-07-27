import { useCallback, useEffect, useState } from 'react';

export function formatCodeCooldownLabel(template: string, seconds: number) {
  return template.replace('{seconds}', String(seconds));
}

export function useCodeCooldown(defaultSeconds = 60) {
  const [remainingSeconds, setRemainingSeconds] = useState(0);

  useEffect(() => {
    if (remainingSeconds <= 0) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      setRemainingSeconds((value) => Math.max(0, value - 1));
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [remainingSeconds]);

  const startCooldown = useCallback(
    (seconds = defaultSeconds) => {
      setRemainingSeconds(seconds);
    },
    [defaultSeconds],
  );

  return {
    isCoolingDown: remainingSeconds > 0,
    remainingSeconds,
    startCooldown,
  };
}
