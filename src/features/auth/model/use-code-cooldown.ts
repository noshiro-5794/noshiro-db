import { useCallback, useEffect, useState } from 'react';

const SECOND_MS = 1_000;

export function remainingCooldownSeconds(deadline: number, now = Date.now()) {
  return Math.max(0, Math.ceil((deadline - now) / SECOND_MS));
}

export function formatCodeCooldownLabel(template: string, seconds: number) {
  return template.replace('{seconds}', String(seconds));
}

export function useCodeCooldown(defaultSeconds = 60) {
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [deadline, setDeadline] = useState<number | null>(null);

  useEffect(() => {
    if (deadline === null) {
      return undefined;
    }

    const updateRemaining = () => {
      const nextRemaining = remainingCooldownSeconds(deadline);
      setRemainingSeconds(nextRemaining);
      if (nextRemaining === 0) setDeadline(null);
    };

    updateRemaining();
    const timer = window.setInterval(updateRemaining, 250);

    return () => {
      window.clearInterval(timer);
    };
  }, [deadline]);

  const startCooldown = useCallback(
    (seconds = defaultSeconds) => {
      const safeSeconds = Number.isFinite(seconds) ? Math.max(0, Math.ceil(seconds)) : defaultSeconds;
      setRemainingSeconds(safeSeconds);
      setDeadline(safeSeconds > 0 ? Date.now() + safeSeconds * SECOND_MS : null);
    },
    [defaultSeconds],
  );

  return {
    isCoolingDown: remainingSeconds > 0,
    remainingSeconds,
    startCooldown,
  };
}
