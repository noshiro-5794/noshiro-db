import { createMemoryHistory } from '@tanstack/react-router';
import { describe, expect, it } from 'vitest';
import { validateSearchPageSearch } from '@/shared/routing/route-search';
import { createAppRouter } from './router';

describe('application router', () => {
  it.each([
    ['/docs/introduction', { slug: 'introduction' }],
    ['/community/posts/42', { postId: '42' }],
    ['/reviews/12', { reviewId: '12' }],
    ['/users/7/collections/9', { collectionId: '9', userId: '7' }],
    ['/reviews/12/edit', { reviewId: '12' }],
    ['/entities/550e8400-e29b-41d4-a716-446655440000/graph', { subjectId: '550e8400-e29b-41d4-a716-446655440000' }],
  ])('matches %s with typed path parameters', async (href, expectedParams) => {
    const router = createAppRouter(createMemoryHistory({ initialEntries: [href] }));

    await router.load();

    expect(router.state.matches.at(-1)?.params).toEqual(expectedParams);
  });

  it('preserves search and hash state', async () => {
    const router = createAppRouter(createMemoryHistory({ initialEntries: ['/search?keyword=test&page=2#results'] }));

    await router.load();

    expect(router.state.location.pathname).toBe('/search');
    expect(router.state.location.searchStr).toBe('?keyword=test&page=2');
    expect(router.state.location.hash).toBe('results');
  });

  it('wires route search validation before pages consume it', () => {
    const router = createAppRouter(createMemoryHistory());

    expect(router.routesByPath['/search'].options.validateSearch).toBe(validateSearchPageSearch);
  });

  it.each([
    ['/community/posts/$postId', '/community/posts'],
    ['/reviews/$reviewId', '/reviews/$reviewId/edit'],
  ] as const)('keeps the public detail route %s outside the authentication boundary', (publicPath, protectedPath) => {
    const router = createAppRouter(createMemoryHistory());

    expect(router.routesByPath[publicPath].options.component?.name).not.toBe('AuthenticatedRoute');
    expect(router.routesByPath[protectedPath].options.component?.name).toBe('AuthenticatedRoute');
  });

  it.each(['/community/posts/0', '/users/not-a-number', '/reviews/-3', '/entities/not-a-uuid'])(
    'rejects invalid path parameters for %s',
    async (href) => {
      const router = createAppRouter(createMemoryHistory({ initialEntries: [href] }));

      await router.load();

      expect(router.state.matches.some((match) => match.status === 'notFound')).toBe(true);
    },
  );

  it('uses the root not-found boundary for unknown routes', async () => {
    const router = createAppRouter(createMemoryHistory({ initialEntries: ['/missing-route'] }));

    await router.load();

    expect(router.state.matches.at(-1)?.globalNotFound).toBe(true);
  });

  it('configures application-level pending and error boundaries', () => {
    const router = createAppRouter(createMemoryHistory());

    expect(router.options.defaultPendingComponent).toBeTypeOf('function');
    expect(router.options.defaultErrorComponent).toBeTypeOf('function');
    expect(router.options.defaultOnCatch).toBeTypeOf('function');
  });
});
