import { createMemoryHistory } from '@tanstack/react-router';
import { describe, expect, it } from 'vitest';
import { createAppRouter } from './router';

describe('application router', () => {
  it.each([
    ['/docs/introduction', { slug: 'introduction' }],
    ['/community/posts/42', { postId: '42' }],
    ['/users/7/collections/9', { collectionId: '9', userId: '7' }],
    ['/reviews/12/edit', { reviewId: '12' }],
    ['/subjects/subject-id/graph', { subjectId: 'subject-id' }],
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

  it('uses the root not-found boundary for unknown routes', async () => {
    const router = createAppRouter(createMemoryHistory({ initialEntries: ['/missing-route'] }));

    await router.load();

    expect(router.state.matches.at(-1)?.globalNotFound).toBe(true);
  });
});
