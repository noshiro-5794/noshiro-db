import { useEffect, useState } from 'react';

export function useVisibleOnce(rootMargin = '240px') {
  const [target, setTarget] = useState<Element | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (!target || isVisible) return undefined;
    if (!('IntersectionObserver' in window)) {
      setIsVisible(true);
      return undefined;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );
    observer.observe(target);

    return () => {
      observer.disconnect();
    };
  }, [isVisible, rootMargin, target]);

  return { isVisible, ref: setTarget };
}
