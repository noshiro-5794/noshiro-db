import type { Transition, Variants } from 'motion/react';

/**
 * Motion values for the JS-driven animations.
 *
 * These mirror `--ui-ease-*` and `--ui-transition-*` in `tokens.css`, which
 * style the CSS-driven half (hover colours, sticky-bar elevation). Change both
 * together: the stylesheet cannot read a TS constant, and a component should
 * not invent its own curve.
 */
const easeStandard = [0.22, 1, 0.36, 1] as const;

const slowSeconds = 0.26;
const fastSeconds = 0.16;

const enterTransition: Transition = { duration: slowSeconds, ease: easeStandard };

/** Staggers a column of hero elements without each one naming its own delay. */
export const heroStackVariants: Variants = {
  hidden: {},
  visible: { transition: { delayChildren: 0.04, staggerChildren: 0.07 } },
};

export const enterVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, transition: enterTransition, y: 0 },
};

/** Reveals a section the first time it scrolls into view. */
export const revealViewport = { margin: '0px 0px -12% 0px', once: true } as const;

export const revealVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, transition: { ...enterTransition, duration: fastSeconds + 0.1 }, y: 0 },
};
