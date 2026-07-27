import {
  useLocation as useRouterLocation,
  useNavigate as useRouterNavigate,
  useRouter,
  useRouterState,
} from '@tanstack/react-router';
import { useCallback, useMemo } from 'react';
import type { Location, NavigateOptions, RouterNavigateBridgeProps, SearchParamsSetter } from './types';

export function useLocation<State = unknown>(): Location<State> {
  const location = useRouterLocation();

  return useMemo(
    () => ({
      hash: location.hash ? `#${location.hash}` : '',
      key:
        location.state.__TSR_index === 0 ? 'default' : (location.state.__TSR_key ?? String(location.state.__TSR_index)),
      pathname: location.pathname,
      search: location.searchStr,
      state: location.state as State,
    }),
    [location.hash, location.pathname, location.searchStr, location.state],
  );
}

export function useNavigate() {
  const navigate = useRouterNavigate() as unknown as (options: RouterNavigateBridgeProps) => Promise<void>;
  const router = useRouter();

  return useCallback(
    (to: number | string, options?: NavigateOptions) => {
      if (typeof to === 'number') {
        router.history.go(to);
        return Promise.resolve();
      }

      return navigate({
        replace: options?.replace,
        state: options?.state,
        to,
      });
    },
    [navigate, router.history],
  );
}

export function useParams<Params extends Record<string, string | undefined> = Record<string, string | undefined>>() {
  const matches = useRouterState({ select: (state) => state.matches });
  return (matches.at(-1)?.params ?? {}) as Params;
}

export function useSearchParams(): [URLSearchParams, SearchParamsSetter] {
  const router = useRouter();
  const location = useRouterLocation();
  const searchParams = useMemo(() => new URLSearchParams(location.searchStr), [location.searchStr]);

  const setSearchParams = useCallback<SearchParamsSetter>(
    (nextInit, options) => {
      const current = new URLSearchParams(router.state.location.searchStr);
      const resolved = typeof nextInit === 'function' ? nextInit(current) : nextInit;
      const next = resolved instanceof URLSearchParams ? resolved : new URLSearchParams(resolved);
      const query = next.toString();
      const hash = router.state.location.hash ? `#${router.state.location.hash}` : '';
      const href = `${router.state.location.pathname}${query ? `?${query}` : ''}${hash}`;

      if (options?.replace) {
        router.history.replace(href, router.state.location.state);
      } else {
        router.history.push(href, router.state.location.state);
      }
    },
    [router],
  );

  return [searchParams, setSearchParams];
}
