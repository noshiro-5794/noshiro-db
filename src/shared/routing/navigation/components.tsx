import { Link as RouterLink, Navigate as RouterNavigate } from '@tanstack/react-router';
import { forwardRef, type ComponentType, type RefAttributes } from 'react';
import { useLocation } from './hooks';
import type { RouterLinkBridgeProps, RouterNavigateBridgeProps } from './types';

const RouterLinkBridge = RouterLink as unknown as ComponentType<
  RouterLinkBridgeProps & RefAttributes<HTMLAnchorElement>
>;
const RouterNavigateBridge = RouterNavigate as unknown as ComponentType<RouterNavigateBridgeProps>;

export const Link = forwardRef<HTMLAnchorElement, RouterLinkBridgeProps>(function Link(props, ref) {
  return <RouterLinkBridge {...props} ref={ref} />;
});

type NavLinkProps = Omit<RouterLinkBridgeProps, 'className'> & {
  className?: string | ((state: { isActive: boolean }) => string);
  end?: boolean;
};

export const NavLink = forwardRef<HTMLAnchorElement, NavLinkProps>(function NavLink(
  { className, end = false, to, ...props },
  ref,
) {
  const { pathname } = useLocation();
  const targetPath = to.split(/[?#]/u, 1)[0] || '/';
  const isActive = end
    ? pathname === targetPath
    : pathname === targetPath || (targetPath !== '/' && pathname.startsWith(`${targetPath}/`));
  const resolvedClassName = typeof className === 'function' ? className({ isActive }) : className;

  return (
    <Link {...props} ref={ref} aria-current={isActive ? 'page' : undefined} className={resolvedClassName} to={to} />
  );
});

export function Navigate({ replace, state, to }: RouterNavigateBridgeProps) {
  return <RouterNavigateBridge replace={replace} state={state} to={to} />;
}
