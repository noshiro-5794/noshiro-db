import { useCallback, useEffect, useRef, useState } from 'react';

const edgeThreshold = 120;
const maxVelocity = 22;

export function useHorizontalDragScroll() {
  const railRef = useRef<HTMLDivElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const velocityRef = useRef(0);
  const activeRef = useRef(false);
  const lastClientXRef = useRef<number | null>(null);
  const [isActive, setIsActive] = useState(false);

  const stop = useCallback(() => {
    activeRef.current = false;
    velocityRef.current = 0;
    lastClientXRef.current = null;
    setIsActive(false);
    if (frameRef.current !== null) {
      window.cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }
  }, []);

  const run = useCallback(function runFrame() {
    if (!railRef.current || !activeRef.current || velocityRef.current === 0) {
      frameRef.current = null;
      return;
    }
    railRef.current.scrollLeft += velocityRef.current;
    frameRef.current = window.requestAnimationFrame(runFrame);
  }, []);

  const move = useCallback(
    (clientX: number) => {
      const nextClientX = clientX > 0 ? clientX : lastClientXRef.current;
      const rail = railRef.current;
      if (!nextClientX || !rail || !activeRef.current) return;

      lastClientXRef.current = nextClientX;
      const rect = rail.getBoundingClientRect();
      const leftDistance = nextClientX - rect.left;
      const rightDistance = rect.right - nextClientX;
      let velocity = 0;
      if (leftDistance < edgeThreshold) {
        velocity = -Math.max(
          4,
          Math.round(((edgeThreshold - Math.max(0, leftDistance)) / edgeThreshold) * maxVelocity),
        );
      } else if (rightDistance < edgeThreshold) {
        velocity = Math.max(
          4,
          Math.round(((edgeThreshold - Math.max(0, rightDistance)) / edgeThreshold) * maxVelocity),
        );
      }

      velocityRef.current = velocity;
      if (velocity !== 0 && frameRef.current === null) frameRef.current = window.requestAnimationFrame(run);
      if (velocity === 0 && frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
    },
    [run],
  );

  const start = useCallback(() => {
    activeRef.current = true;
    setIsActive(true);
  }, []);

  useEffect(() => {
    if (!isActive) return undefined;
    const handleWindowDragOver = (event: globalThis.DragEvent) => {
      move(event.clientX);
    };
    window.addEventListener('dragover', handleWindowDragOver);
    return () => {
      window.removeEventListener('dragover', handleWindowDragOver);
    };
  }, [isActive, move]);

  useEffect(() => stop, [stop]);

  return { move, railRef, start, stop };
}
