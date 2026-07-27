import type { AnchorHTMLAttributes } from 'react';

export type Location<State = unknown> = {
  hash: string;
  key: string;
  pathname: string;
  search: string;
  state: State;
};

export type NavigateOptions = {
  replace?: boolean;
  state?: unknown;
};

export type RouterLinkBridgeProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> & {
  replace?: boolean;
  state?: unknown;
  to: string;
};

export type RouterNavigateBridgeProps = NavigateOptions & {
  to: string;
};

export type SearchParamsInit = ConstructorParameters<typeof URLSearchParams>[0] | URLSearchParams;
export type SearchParamsSetter = (
  nextInit: SearchParamsInit | ((current: URLSearchParams) => SearchParamsInit),
  options?: Pick<NavigateOptions, 'replace'>,
) => void;
