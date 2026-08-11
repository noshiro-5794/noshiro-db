export function resolvedRouteHref(href: string) {
  return { to: href as never } as const;
}
