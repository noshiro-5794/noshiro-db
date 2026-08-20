import { describe, expect, it } from 'vitest';
import {
  backTargetFromState,
  currentRoutePath,
  returnTargetFromState,
  routeBackState,
  type RouteLocation,
} from './route-state';

type LegacyRouteLocation = Extract<RouteLocation, { pathname: string }>;

function location(overrides: Partial<LegacyRouteLocation> = {}): LegacyRouteLocation {
  return {
    hash: '#section',
    pathname: '/entities/1',
    search: '?tab=details',
    state: null,
    ...overrides,
  };
}

describe('route state', () => {
  it('preserves the complete current route', () => {
    const current = location();

    expect(currentRoutePath(current)).toBe('/entities/1?tab=details#section');
    expect(routeBackState(current, 'Subject')).toEqual({
      from: '/entities/1?tab=details#section',
      fromLabel: 'Subject',
    });
  });

  it('uses a valid internal return route', () => {
    const current = location({ state: { returnTo: '/library?page=2' } });

    expect(backTargetFromState(current, '/')).toBe('/library?page=2');
  });

  it.each(['//example.com', '/\\example.com', '/path\u0000suffix'])('rejects unsafe return route %j', (returnTo) => {
    const current = location({ state: { returnTo } });

    expect(backTargetFromState(current, '/safe')).toBe('/safe');
  });

  it('validates standalone authentication return state', () => {
    expect(returnTargetFromState({ returnTo: '/library?page=2' }, '/')).toBe('/library?page=2');
    expect(returnTargetFromState({ returnTo: '//example.com' }, '/')).toBe('/');
    expect(returnTargetFromState(null, '/')).toBe('/');
  });

  it('does not navigate back to the current route', () => {
    const current = location({ state: { from: '/entities/1?tab=details#section' } });

    expect(backTargetFromState(current, '/search')).toBe('/search');
  });
});
