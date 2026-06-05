import type { Location } from 'react-router-dom';

export type RouteBackState = {
  from?: string;
  fromLabel?: string;
  returnTo?: string;
};

export function currentRoutePath(location: Location) {
  return `${location.pathname}${location.search}${location.hash}`;
}

function isInternalPath(value: unknown): value is string {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//');
}

export function routeBackState(location: Location, fromLabel?: string): RouteBackState {
  return {
    from: currentRoutePath(location),
    fromLabel,
  };
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
