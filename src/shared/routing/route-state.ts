import type {} from '@tanstack/history';

export type RouteBackState = {
  from?: string;
  fromLabel?: string;
  returnTo?: string;
};

declare module '@tanstack/history' {
  interface HistoryState {
    from?: string;
    fromLabel?: string;
    returnTo?: string;
  }
}

export type RouteLocation =
  { href: string; state: unknown } | { hash: string; pathname: string; search: string; state: unknown };

export function currentRoutePath(location: RouteLocation) {
  return 'href' in location ? location.href : `${location.pathname}${location.search}${location.hash}`;
}

function isInternalPath(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.startsWith('/') &&
    !value.startsWith('//') &&
    !value.includes('\\') &&
    !hasControlCharacter(value)
  );
}

function hasControlCharacter(value: string) {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code <= 0x1f || code === 0x7f) return true;
  }

  return false;
}

export function routeBackState(location: RouteLocation, fromLabel?: string): RouteBackState {
  return {
    from: currentRoutePath(location),
    ...(fromLabel === undefined ? {} : { fromLabel }),
  };
}

export function returnTargetFromState(state: unknown, fallback: string) {
  if (typeof state !== 'object' || state === null || !('returnTo' in state)) {
    return fallback;
  }

  return isInternalPath(state.returnTo) ? state.returnTo : fallback;
}

export function backTargetFromState(location: RouteLocation, fallback: string) {
  const state = location.state as RouteBackState | null;
  const currentPath = currentRoutePath(location);

  if (isInternalPath(state?.from) && state.from !== currentPath) {
    return state.from;
  }

  if (isInternalPath(state?.returnTo) && state.returnTo !== currentPath) {
    return state.returnTo;
  }

  return fallback;
}
