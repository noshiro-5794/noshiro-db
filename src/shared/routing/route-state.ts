import type { Location } from '@/shared/routing/navigation';

export type RouteBackState = {
  from?: string;
  fromLabel?: string;
  returnTo?: string;
};

export function currentRoutePath(location: Location) {
  return `${location.pathname}${location.search}${location.hash}`;
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

export function routeBackState(location: Location, fromLabel?: string): RouteBackState {
  return {
    from: currentRoutePath(location),
    fromLabel,
  };
}

export function returnTargetFromState(state: unknown, fallback: string) {
  if (typeof state !== 'object' || state === null || !('returnTo' in state)) {
    return fallback;
  }

  return isInternalPath(state.returnTo) ? state.returnTo : fallback;
}

export function backTargetFromState(location: Location, fallback: string) {
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
