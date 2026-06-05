# Architecture

Noshiro DB frontend uses a feature-oriented structure with shared infrastructure kept separate from product modules.

```text
src/app/       application shell, providers, and global layout
src/config/    environment access
src/features/  product features, API wrappers, query options, and feature components
src/lib/       framework-agnostic infrastructure such as API and query clients
src/pages/     route-level pages
src/routes/    path helpers and route table
src/shared/    reusable UI primitives
src/styles/    global Tailwind CSS and design tokens
```

## Boundaries

- `lib` is for technical infrastructure that does not belong to a product domain.
- `features` is for domain logic such as auth, subjects, library, search, calendar, community, social, docs, and sync.
- `shared/ui` is for reusable UI primitives without domain ownership.
- `pages` compose features into routes.
- `routes` owns path helpers, route metadata, and auth boundaries.

## API Layer

Feature APIs live next to their domain:

- `features/auth/api.ts`
- `features/subjects/api.ts`
- `features/library/api.ts`
- `features/community/api.ts`
- `features/social/api.ts`
- `features/sync/api.ts`

React Query options are defined per feature so pages can stay focused on composition and user flow.

The backend currently separates social/community APIs from user-owned record APIs:

- `/api/users/` keeps auth, profile, subject marks, progress, tags, reviews, collections, and public profile resources.
- `/api/community/` owns follows, followers, following, activities, feed, notifications, bookmarks, reactions, comments, and reports.

Frontend modules follow the same split: user-owned library/review/collection flows stay in their feature modules, while community interaction and public activity flows use `features/community` and `features/social`.

## Route Pages

Route pages live in `src/pages` and compose feature modules into user-facing flows.

Public pages:

- Home
- Search
- Calendar
- Subject
- Subject Graph
- Docs

Authenticated pages:

- Workspace Home
- Me and public profile shortcuts
- Settings
- Library
- Collections
- Reviews
- Bookmarks
- Notifications
- Activity/community pages

Admin pages are authenticated and additionally depend on the backend role returned for the current user.

## Internationalization

Global UI messages live in `src/features/i18n/messages.ts`. A few content-heavy pages keep local content maps:

- `src/features/docs/content/docs.ts` for frontend-owned docs pages
- `src/pages/MePage.tsx` for compact profile-page labels

Copy should stay neutral for mixed anime and galgame entries. Use status labels such as planned, in progress, completed, on hold, and dropped for subject-level state. Episode-specific controls may use watched language because they apply to anime episodes.

## Static Assets

Production static files live under `public/`:

- `brand/icon.svg`
- favicon and Apple touch icon files
- PWA icons and `site.webmanifest`
- placeholder images used by cards and avatars
