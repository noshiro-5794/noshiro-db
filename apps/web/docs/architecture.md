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

Decoders are the text boundary as well as the type boundary. Providers publish synopses as small HTML fragments, so
`buildSubjectDetail` runs them through `plainText()` in `src/shared/lib/text.ts` before anything renders them. A
surface that receives a description can draw it as text and assume it is text.

The backend resource split is mirrored by the frontend:

- `/api/v1/users/` owns auth, profile, library entries, progress, tags, reviews, and collections.
- `/api/v1/community/` owns follows, activities, posts, notifications, bookmarks, reactions, comments, and reports.
- `/api/v1/index/` owns entity, episode, credit, character, relation, release, metric, evidence, and calendar resources.
- `/api/v1/operations/import-jobs/` owns async import jobs.
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

Production static files live under `public/`: the generated app icons, PWA metadata, and the social card. Missing
artwork is drawn at runtime instead of shipped as an image — see `src/shared/lib/identity.ts` for the initials and
tone used by avatars and covers. Build output remains in `dist/` and is not source code.

## Conventions

Modules are named after the concern they own, not after the slice they sit in. The path already carries the domain,
so the subject slice fetches through `entities/subject/api/client.ts` and describes its queries in
`entities/subject/model/queries.ts`, rather than repeating "subject" in every filename. A file that belongs to
several slices, such as the poster tile shared by the catalogue and the landing showcase, lives in the entity that
owns the data (`entities/subject/ui/SubjectPosterCard.tsx`) instead of being copied into each consumer.

Comments explain why a decision was made, in English. A comment that restates the line beneath it is noise; the
reasoning belongs in the commit message. Docstrings on exported components and hooks get one line about the
contract, not a restatement of the props.

Enforcement: `tsc` runs with `strict`, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`,
`verbatimModuleSyntax`, and `erasableSyntaxOnly`; ESLint extends `strictTypeChecked` and rejects imports that bypass
a slice's public `index.ts`. Prettier owns formatting at 120 columns. `pnpm check` runs the whole chain.

### Interface scale

The primitives follow plane's design system (`@makeplane/propel`), whose rules are mirrored into `tokens.css` rather
than imported: a repository that runs two stacks should own its tokens, and propel is a Tailwind v4 CSS layer built
for plane's own component set.

- **Controls** pick a rung and take everything from it: `--ui-control-height-xs` (28px), `--ui-control-height`
  (32px) or `--ui-control-height-lg` (36px), with `--ui-control-padding-x*`, `--ui-control-gap` and
  `--ui-control-glyph*` travelling alongside. One row uses one rung; a small control is not a large control with
  smaller text. `Button`, `Input` and `InputGroup` all default to the same rung, and a component that leaves it
  implicit is the bug: the catalogue toolbar mixed 32px and 36px controls in one row until every list toolbar
  agreed on `lg`.
- **Filter triggers** share one anatomy, in `FilterTrigger.tsx`: the field name in the muted slot and the value in
  the strong one, with no value at all while the filter narrows nothing. Leading with the value turns the unset
  state — the word "All" — into a phrase that reads as a category rather than as an empty filter. `emptyValue`
  names the option that means "not narrowing" when that option is a word instead of the empty string.
- **Radius** has three levels: `--ui-radius-control` (6px) for anything you click, `--ui-radius-surface` (8px) for
  the surface that holds them (menus, popovers, cards, dialogs) and `--ui-radius-frame` (10px) for a full-height
  panel such as the navigation drawer.
- **Focus** is always the soft halo (`--ui-focus-halo` at 2px with a 1px offset), never a hard ring.
- **Motion** is named, not inline: `--ui-transition-fast/standard/slow` with `--ui-ease-standard` for transforms and
  `--ui-ease-gentle` for colour. `src/shared/lib/motion.ts` mirrors the two curves for the `motion` half of the app;
  `global.css` reduces both halves for visitors who ask for less motion.
- **Prose** keeps the measure the review bodies set, `max-w-3xl`. A synopsis capped at nothing runs the width of a
  1400px page, which is a hundred and fifty characters a line.
- **Empty states** are a section's quiet line (`EmptyState variant="inline"`) when the section sits inside a page
  that has other content, and a bordered card when the empty state is the page. `ResultsState` takes that choice as
  `emptyVariant`.
