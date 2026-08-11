import { expect, test, type Page, type Route } from '@playwright/test';

const subjectId = '01980f00-0000-7000-8000-000000000001';
const publicPostId = 42;
const publicReviewId = 12;

const emptyPage = {
  count: 0,
  next: null,
  previous: null,
  results: [],
};

const subject = {
  id: subjectId,
  title: 'Graph smoke subject',
  title_cn: null,
  subject_type: 'anime',
  date: '2026-07-29',
  platform: 'TV',
  nsfw: false,
  episode_count: 1,
  staff_count: 0,
  character_count: 0,
  tags: ['science fiction'],
};

const publicAuthor = {
  id: 7,
  nickname: 'Public author',
  avatar: null,
};

const publicPost = {
  id: publicPostId,
  content: 'A public post that guests can read.',
  visibility: 'public',
  is_spoiler: false,
  is_nsfw: false,
  is_locked: false,
  reply_count: 0,
  reaction_count: 3,
  created_at: '2026-07-29T08:00:00Z',
  author: publicAuthor,
};

const publicReview = {
  id: publicReviewId,
  title: 'Public review fixture',
  content: 'A public review that guests can read.',
  is_public: true,
  is_spoiler: false,
  reaction_count: 2,
  created_at: '2026-07-29T08:00:00Z',
  subject,
  user: publicAuthor,
};

const publicProfile = {
  ...publicAuthor,
  bio: 'Public profile fixture',
  is_following: false,
  stats: {
    subject_count: 1,
    review_count: 0,
    collection_count: 0,
    following_count: 0,
    follower_count: 0,
  },
};

const activity = {
  id: 91,
  activity_type: 'user_subject_created',
  created_at: '2026-07-29T08:00:00Z',
  reaction_count: 0,
  user: publicAuthor,
  subject,
  viewer_state: { has_liked: false },
};

const userSubject = {
  id: 1,
  status: 'doing',
  simple_rating: 4,
  rating: '8.5',
  comment: 'Continuing this week',
  watch_start_date: '2026-07-01',
  watch_end_date: null,
  is_public: true,
  updated_at: '2026-07-29T08:00:00Z',
  subject: {
    ...subject,
    image: null,
    image_thumbnail: null,
  },
};

const progress = {
  subject_id: subjectId,
  user_subject_id: null,
  total_episodes: 1,
  finished_count: 0,
  finished_episode_ids: [],
  episodes: [],
};

function apiEnvelope(data: unknown) {
  return { code: 0, message: 'ok', data };
}

async function fulfillApi(route: Route, data: unknown, headers?: Record<string, string>) {
  await route.fulfill({
    contentType: 'application/json',
    headers,
    json: apiEnvelope(data),
    status: 200,
  });
}

async function currentReturnTarget(page: Page) {
  return page.evaluate(() => {
    const state: unknown = window.history.state;
    if (typeof state !== 'object' || state === null || !('returnTo' in state)) return null;
    return typeof state.returnTo === 'string' ? state.returnTo : null;
  });
}

async function mockPublicApi(page: Page) {
  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      const path = new URL(route.request().url()).pathname;

      if (path === '/api/users/token/refresh/') {
        await route.fulfill({
          contentType: 'application/json',
          json: { code: 401, message: 'No active session', data: null },
          status: 401,
        });
        return;
      }

      if (path === '/api/index/calendar/') {
        await fulfillApi(route, [
          {
            weekday: { id: 3, en: 'Wed' },
            items: [
              {
                subject_id: subjectId,
                subject_type: 'anime',
                title: subject.title,
                title_cn: null,
                image_thumbnail: null,
                platform: 'TV',
                nsfw: false,
                weekday_en: 'Wed',
                doing: 12,
              },
            ],
          },
        ]);
        return;
      }

      if (path === `/api/community/posts/${String(publicPostId)}/`) {
        await fulfillApi(route, publicPost);
        return;
      }

      if (path === `/api/users/reviews/${String(publicReviewId)}/`) {
        await fulfillApi(route, publicReview);
        return;
      }

      if (path === `/api/index/subjects/${subjectId}/`) {
        await fulfillApi(route, subject);
        return;
      }

      if (path.startsWith(`/api/index/subjects/${subjectId}/`)) {
        await fulfillApi(route, emptyPage);
        return;
      }

      await fulfillApi(route, emptyPage);
    },
  );
}

async function mockAuthenticatedApi(page: Page) {
  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      const path = new URL(route.request().url()).pathname;

      if (path === '/api/users/token/refresh/') {
        await fulfillApi(route, { access: 'e2e-access-token' });
        return;
      }

      if (path === '/api/users/me/profile/') {
        await fulfillApi(route, {
          user_id: 1,
          email: 'noshiro@example.com',
          nickname: 'Noshiro',
          avatar: null,
          bio: '',
          is_staff: false,
          is_superuser: false,
          language: 'en-US',
          appearance: 'light',
        });
        return;
      }

      if (path === '/api/users/me/subjects/') {
        await fulfillApi(route, { ...emptyPage, count: 1, results: [userSubject] });
        return;
      }

      if (path === '/api/community/notifications/unread-count/') {
        await fulfillApi(route, { unread_count: 0 });
        return;
      }

      if (path === `/api/index/subjects/${subjectId}/`) {
        await fulfillApi(route, subject);
        return;
      }

      if (path === `/api/users/me/subjects/${subjectId}/context/`) {
        await fulfillApi(route, {
          is_marked: false,
          user_subject: null,
          tags: [],
          rating_details: [],
          reviews: [],
          progress,
        });
        return;
      }

      if (path === `/api/users/me/subjects/${subjectId}/episodes/progress/`) {
        await fulfillApi(route, progress);
        return;
      }

      if (path.endsWith('/staff/roles/')) {
        await fulfillApi(route, { roles: [] });
        return;
      }

      await fulfillApi(route, emptyPage);
    },
  );
}

async function mockLanguageSwitchLoginApi(page: Page) {
  let refreshRequestCount = 0;
  let refreshCookie = 'login-refresh-token';

  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      const path = new URL(route.request().url()).pathname;

      if (path === '/api/users/token/refresh/') {
        refreshRequestCount += 1;
        const requestCookie = route.request().headers()['cookie'] ?? '';
        if (!requestCookie.includes(`e2e_refresh=${refreshCookie}`)) {
          await route.fulfill({
            contentType: 'application/json',
            json: { code: 401, message: 'No active session', data: null },
            status: 401,
          });
          return;
        }

        refreshCookie = `rotated-refresh-token-${String(refreshRequestCount)}`;
        await fulfillApi(
          route,
          { access: 'refreshed-access-token' },
          {
            'set-cookie': `e2e_refresh=${refreshCookie}; HttpOnly; Path=/api/users/; SameSite=Lax; Secure`,
          },
        );
        return;
      }

      if (path === '/api/users/login/password/') {
        await fulfillApi(
          route,
          { access: 'login-access-token' },
          {
            'set-cookie': `e2e_refresh=${refreshCookie}; HttpOnly; Path=/api/users/; SameSite=Lax; Secure`,
          },
        );
        return;
      }

      if (path === '/api/users/me/profile/') {
        await fulfillApi(route, {
          user_id: 1,
          email: 'noshiro@example.com',
          nickname: 'Noshiro',
          avatar: null,
          bio: '',
          is_staff: false,
          is_superuser: false,
          language: 'ja-JP',
          appearance: 'light',
        });
        return;
      }

      if (path === '/api/community/notifications/unread-count/') {
        await fulfillApi(route, { unread_count: 0 });
        return;
      }

      await fulfillApi(route, emptyPage);
    },
  );

  return () => refreshRequestCount;
}

async function mockActivityProfileApi(page: Page) {
  let refreshRequestCount = 0;
  let publicSubjectOrdering: string | null = null;

  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;

      if (path === '/api/users/token/refresh/') {
        refreshRequestCount += 1;
        await new Promise((resolve) => setTimeout(resolve, 50));
        await fulfillApi(route, { access: 'activity-access-token' });
        return;
      }

      if (path === '/api/users/me/profile/') {
        await fulfillApi(route, {
          user_id: 1,
          email: 'noshiro@example.com',
          nickname: 'Noshiro',
          avatar: null,
          bio: '',
          is_staff: false,
          is_superuser: false,
          language: 'en-US',
          appearance: 'light',
        });
        return;
      }

      if (path === '/api/community/me/feed/') {
        await fulfillApi(route, { ...emptyPage, count: 1, results: [activity] });
        return;
      }

      if (path === `/api/users/${String(publicAuthor.id)}/profile/`) {
        await fulfillApi(route, publicProfile);
        return;
      }

      if (path === `/api/users/${String(publicAuthor.id)}/subjects/`) {
        publicSubjectOrdering = url.searchParams.get('ordering');
        if (publicSubjectOrdering !== '-id') {
          await route.fulfill({
            contentType: 'application/json',
            json: { code: 400, message: 'Unsupported ordering', data: null },
            status: 400,
          });
          return;
        }
      }

      if (path === '/api/community/notifications/unread-count/') {
        await fulfillApi(route, { unread_count: 0 });
        return;
      }

      await fulfillApi(route, emptyPage);
    },
  );

  return {
    getPublicSubjectOrdering: () => publicSubjectOrdering,
    getRefreshRequestCount: () => refreshRequestCount,
  };
}

test.beforeEach(async ({ page }) => {
  await mockPublicApi(page);
});

test.afterEach(async ({ page }) => {
  expect(await page.pageErrors()).toEqual([]);
});

test('public home opens the catalog and renders API data', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Collect. Preserve. Relive.' })).toBeVisible();
  await expect(page.getByText('Graph smoke subject').first()).toBeVisible();

  await page.getByRole('link', { name: 'Explore catalog' }).click();
  await expect(page).toHaveURL(/\/search$/u);
  await expect(page.getByRole('searchbox', { name: 'Keyword' })).toBeVisible();
  await expect(page.getByText('Graph smoke subject').first()).toBeVisible();

  await page.goto('/calendar');
  await expect(page.getByRole('heading', { name: 'Calendar' })).toBeVisible();
});

test('protected routes preserve the destination while redirecting to login', async ({ page }) => {
  await page.goto('/library?keyword=noshiro');

  await expect(page).toHaveURL(/\/login$/u);
  await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible();
  await expect.poll(() => currentReturnTarget(page)).toBe('/library?keyword=noshiro');
  await expect(page.getByRole('textbox', { name: 'Email' })).toBeVisible();
  await expect(page.getByLabel('Password')).toBeVisible();
});

test('guests can open public details while authenticated write actions stay gated', async ({ page }) => {
  await page.goto(`/reviews/${String(publicReviewId)}`);

  await expect(page).toHaveURL(new RegExp(`/reviews/${String(publicReviewId)}$`, 'u'));
  await expect(page.locator('h1')).toHaveText(publicReview.title);
  await expect(page.getByText(publicReview.content)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Log in to interact' })).toHaveAttribute('href', '/login');
  await expect(page.getByText('Log in to join the discussion')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Edit' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Delete' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Report' })).toHaveCount(0);

  await page.goto(`/community/posts/${String(publicPostId)}`);

  await expect(page).toHaveURL(new RegExp(`/community/posts/${String(publicPostId)}$`, 'u'));
  await expect(page.locator('h1')).toHaveText('Post detail');
  await expect(page.getByText(publicPost.content)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Log in to interact' })).toHaveAttribute('href', '/login');
  await expect(page.getByText('Log in to join the discussion')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Follow author' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Edit' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Delete' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Report' })).toHaveCount(0);
});

test('login keeps the session when the account language differs from the browser', async ({ page }) => {
  await page.unrouteAll({ behavior: 'wait' });
  const getRefreshRequestCount = await mockLanguageSwitchLoginApi(page);
  await page.goto('/library?keyword=noshiro');

  await expect(page).toHaveURL(/\/login$/u);
  await expect.poll(() => currentReturnTarget(page)).toBe('/library?keyword=noshiro');
  const refreshRequestCountBeforeLogin = getRefreshRequestCount();
  await page.getByRole('textbox', { name: 'Email' }).fill('noshiro@example.com');
  await page.getByLabel('Password').fill('correct-password');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();

  await expect(page).toHaveURL(/\/library\?keyword=noshiro$/u);
  await expect(page.locator('h1')).toHaveText('ライブラリ');
  await expect.poll(getRefreshRequestCount).toBe(refreshRequestCountBeforeLogin);

  await page.reload();
  await expect(page).toHaveURL(/\/library\?keyword=noshiro$/u);
  await expect(page.locator('h1')).toHaveText('ライブラリ');
  await expect.poll(getRefreshRequestCount).toBe(refreshRequestCountBeforeLogin + 1);

  await page.evaluate(() => window.dispatchEvent(new Event('languagechange')));
  await expect(page.locator('h1')).toHaveText('ライブラリ');

  await page.setViewportSize({ height: 844, width: 390 });
  await page.goto('/community/posts');
  await expect(page.locator('h1')).toHaveText('タイムライン');
  await expect(page.getByRole('button', { name: 'フォロー中', exact: true })).toHaveCSS('white-space', 'nowrap');
});

test('activity survives reload and opens the avatar profile without invalid queries', async ({ page }) => {
  await page.unrouteAll({ behavior: 'wait' });
  const { getPublicSubjectOrdering, getRefreshRequestCount } = await mockActivityProfileApi(page);

  await page.goto('/community/posts');
  await expect(page.getByRole('img', { name: publicAuthor.nickname })).toBeVisible();
  await expect.poll(getRefreshRequestCount).toBe(1);

  await page.reload();
  await expect(page.getByRole('img', { name: publicAuthor.nickname })).toBeVisible();
  await expect.poll(getRefreshRequestCount).toBe(2);

  await page.getByRole('img', { name: publicAuthor.nickname }).click();
  await expect(page).toHaveURL(new RegExp(`/users/${String(publicAuthor.id)}$`, 'u'));
  await expect(page.locator('h1')).toHaveText(publicAuthor.nickname);
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect.poll(getPublicSubjectOrdering).toBe('-id');
});

test('authenticated workspace opens core views', async ({ page }) => {
  await page.unrouteAll({ behavior: 'wait' });
  await mockAuthenticatedApi(page);
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Home' })).toBeVisible();
  await expect(page.getByText('Welcome back')).toBeVisible();

  await page.getByRole('button', { name: 'Noshiro', exact: true }).click();
  await expect(page.getByText('noshiro@example.com')).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Profile' })).toBeVisible();
  await page.keyboard.press('Escape');

  await page.getByRole('navigation').getByRole('link', { name: 'Library', exact: true }).click();
  await expect(page).toHaveURL(/\/library$/u);
  await expect(page.locator('h1')).toHaveText('Library');
  await expect(page.getByText(subject.title).first()).toBeVisible();

  await page.setViewportSize({ height: 900, width: 1440 });
  await page.goto(`/subjects/${subjectId}`);
  await expect(page.locator('h1')).toHaveText(subject.title);

  const subjectNavigationOffset = await page.locator('[data-slot="subject-section-nav"]').evaluate((navigation) => {
    const pageTopbar = document.querySelector<HTMLElement>('[data-slot="page-topbar"]');
    if (!pageTopbar) return Number.POSITIVE_INFINITY;
    return navigation.getBoundingClientRect().top - pageTopbar.getBoundingClientRect().bottom;
  });
  expect(Math.abs(subjectNavigationOffset)).toBeLessThanOrEqual(1);

  const markButton = page.getByRole('button', { name: 'Mark subject', exact: true });
  await expect(markButton).toBeEnabled();
  const markIconSize = await markButton.locator('svg').evaluate((icon) => {
    const bounds = icon.getBoundingClientRect();
    return Math.max(bounds.width, bounds.height);
  });
  expect(markIconSize).toBeLessThanOrEqual(16.5);
  await markButton.click();

  const markDialog = page.getByRole('dialog');
  await expect(markDialog).toBeVisible();
  await expect(markDialog.locator('[data-slot="dialog-footer"]')).toBeVisible();
  const markDialogBounds = await markDialog.evaluate((dialog) => {
    const bounds = dialog.getBoundingClientRect();
    return { height: bounds.height, width: bounds.width };
  });
  expect(markDialogBounds.width).toBeLessThanOrEqual(672);
  expect(markDialogBounds.height).toBeLessThanOrEqual(868);
  await markDialog.getByRole('button', { name: 'Close' }).click();
  await expect(markDialog).toBeHidden();

  await page.goto(`/reviews/new?subjectId=${subjectId}`);
  await expect(page.getByRole('heading', { name: 'New review' })).toBeVisible();
  const toolbarOffset = await page.locator('.review-editor-toolbar').evaluate((toolbar) => {
    const editor = toolbar.parentElement;
    return editor ? toolbar.getBoundingClientRect().top - editor.getBoundingClientRect().top : Number.POSITIVE_INFINITY;
  });
  expect(toolbarOffset).toBeLessThanOrEqual(2);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/subjects/${subjectId}`);
  await expect(page.locator('h1')).toHaveText(subject.title);
  await expect(page.getByRole('link', { name: 'My mark', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Infobox/u })).toBeVisible();
  await expect(page.getByRole('button', { name: /Staff/u })).toBeVisible();

  await page.getByRole('button', { name: 'Open navigation' }).click();
  const navigationDialog = page.getByRole('dialog');
  await expect(navigationDialog).toBeVisible();
  await expect(navigationDialog.getByRole('link', { name: 'Library', exact: true })).toBeVisible();
  await navigationDialog.getByRole('button', { name: 'Close navigation' }).click();
  await expect(navigationDialog).toBeHidden();
});

test('knowledge graph paints non-empty canvas pixels', async ({ page }) => {
  await page.goto(`/subjects/${subjectId}/graph`);

  const canvas = page.locator('canvas');
  await expect(canvas).toBeVisible();
  await expect(page.getByText('Nodes', { exact: true })).toBeVisible();
  await expect
    .poll(async () =>
      canvas.evaluate((element) => {
        if (!(element instanceof HTMLCanvasElement)) return false;
        const context = element.getContext('2d');
        if (!context || element.width === 0 || element.height === 0) return false;
        const pixels = context.getImageData(0, 0, element.width, element.height).data;
        for (let index = 3; index < pixels.length; index += 4) {
          if (pixels[index] !== 0) return true;
        }
        return false;
      }),
    )
    .toBe(true);
});
