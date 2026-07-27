# Architecture

Noshiro DB frontend uses a layered, domain-oriented architecture. Dependencies flow in one direction:

```text
app -> pages -> widgets -> features -> entities -> shared
```

Each layer may use layers to its right, but never layers to its left. ESLint enforces this rule and requires
consumers to import entity, feature, and widget slices through their public `index.ts` entry point.

## Source Layers

```text
src/app/       application bootstrap, providers, router, shell, and global styles
src/pages/     route-level composition grouped by route domain
src/widgets/   reusable, product-aware sections composed from features and entities
src/features/  user interactions and use cases
src/entities/  domain data access, query definitions, models, and entity UI
src/shared/    domain-independent infrastructure, utilities, and UI primitives
```

`src/main.tsx` is the browser entry point. It mounts application providers and the router, but contains no product
logic.

## Slice Structure

Entities, features, and widgets are independent slices. A slice uses only the segments it needs:

```text
slice/
  api/       transport calls owned by the slice
  model/     query definitions, state, and domain helpers
  ui/        slice-owned React components
  index.ts   public API for other slices and layers
```

Internal files use relative imports. External consumers use only the public API, for example
`@/entities/subject`, never `@/entities/subject/model/subject-queries`.

Pages are grouped by route domain. Page-local helpers, content, and UI may live beneath that page directory and are
not public cross-page APIs.

## Domain Ownership

- `entities/session` owns authentication transport, the current session model, and profile access.
- `entities/subject` owns subject search/detail data and subject presentation.
- `entities/library` owns marks, progress, tags, ratings, reviews, and collections.
- `entities/community` owns posts, comments, reactions, bookmarks, follows, activity, and notifications.
- `entities/user` owns public user profiles and public user content queries.
- `features/auth` owns login and registration interaction helpers.
- `features/community` owns community mutations that coordinate entity caches and interactive community UI.
- `features/search` owns client-side search filters and calendar search transformations.
- `features/reviews` owns Markdown editing and sanitized rendering.
- `features/admin-sync` owns administrative synchronization operations.

Widgets compose these slices into reusable product sections such as the home dashboard, notification control, public
content presentation, and public footer.

## API Layer

`src/shared/api` contains the HTTP client and transport contracts. Contracts are split by backend resource domain in
`src/shared/api/contracts/`; its `index.ts` is the only public import path. Domain-owned API calls and TanStack Query
definitions remain in their entity or feature slice.

The backend resource split is mirrored by the frontend:

- `/api/users/` owns auth, profile, marks, progress, tags, reviews, collections, and public profile resources.
- `/api/community/` owns follows, activities, posts, notifications, bookmarks, reactions, comments, and reports.
- administrative synchronization routes are owned by `features/admin-sync`.

## Routing

`src/app/router/router.tsx` defines the TanStack Router tree, route-level lazy loading, and access boundaries.
Application code uses the adapters in `src/shared/routing/navigation/` for links and navigation state. Shared path
builders in `src/shared/routing/paths.ts` keep URL construction consistent and independently testable.

## Internationalization

`src/shared/i18n/catalogs/` contains business-focused message catalogs. Every catalog defines Chinese, English, and
Japanese together; `defineMessages()` checks key parity at compile time, and `catalog.test.ts` verifies the assembled
catalog at runtime.

Content-heavy documentation remains page-local in `src/pages/docs/content/docs.ts`. Locale-sensitive dates and
weekdays use `Intl` through shared formatting helpers instead of duplicated label maps.

## Global Concerns

- Providers are composed in `src/app/providers/AppProviders.tsx`.
- Application chrome lives in `src/app/shell/`.
- Global Tailwind CSS and design tokens live in `src/app/styles/global.css`.
- Environment parsing lives in `src/shared/config/env.ts`.
- The Query client lives in `src/shared/query/query-client.ts`.
- Reusable, domain-independent controls live in `src/shared/ui/`.

## Static Assets

Production static files live under `public/`, including the brand icon, PWA metadata, social image, and placeholder
images. Build output remains in `dist/` and is not source code.
