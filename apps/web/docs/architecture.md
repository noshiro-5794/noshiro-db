# Web architecture

The Web application is a React SPA. Application providers compose TanStack
Router, TanStack Query, session state, and localization. Its HTTP client
consumes the versioned API contract.

## Source layers

Dependencies flow from `app` to `pages`, `widgets`, `features`,
`entities`, and `shared`. A layer can use any layer to its right.

| Package        | Responsibility                                                        |
| -------------- | --------------------------------------------------------------------- |
| `src/app`      | Bootstrap, providers, router, shell, and global styles                |
| `src/pages`    | Route-level composition and page-local content                        |
| `src/widgets`  | Reusable product sections composed from features and entities         |
| `src/features` | User interactions and workflows                                       |
| `src/entities` | Domain queries, models, and reusable domain UI                        |
| `src/shared`   | HTTP, configuration, routing helpers, localization, and UI primitives |

Entities, features, and widgets organize their code into slices. A slice may
have `api/`, `model/`, and `ui/` segments. Consumers import its public
`index.ts` entry point. ESLint checks layer direction and slice imports.

## Routing and data

`src/app/router/router.tsx` owns route access and lazy page loading.
Path builders and navigation adapters live in `src/shared/routing/`.
The route prefix may use catalogue terminology independent of the names of
upstream provider objects.

`src/shared/api/` owns the HTTP client, wire contracts, and decoders.
Domain-specific calls and query definitions live with the entities and
features that use them. Decoders normalize provider values, including
synopsis text. Markdown rendering belongs to the review feature.

The API publishes resource families under `/api/v1/auth/`,
`/api/v1/users/`, `/api/v1/community/`, `/api/v1/index/`, and
`/api/v1/operations/`. Update the Web transport types and decoders alongside
any payload change on the API.

## Localization and design

Message catalogs live in `src/shared/i18n/catalogs/`. Each catalog defines
Chinese, English, and Japanese keys together. Public documentation lives
in `src/pages/docs/content/`, with one module per locale and navigation
derived from page definitions.

Shared primitives use the global control sizes, radii, focus indicators,
and motion tokens. Product features compose those primitives. Page headings,
filter text, and empty states use the same message catalogs as the surrounding
controls.

`public/` holds production static assets, including generated icons and
manifest metadata. Vite writes the release build to `dist/`.

## Conventions

- Name files for the concern they own. Let the slice path carry the domain.
- Use relative imports within a slice and the public entry point across slices.
- Keep domain use cases in features and entities. Keep transport and reusable UI in shared.
- Use typed, decoded API values at the rendering boundary.
- Write decision-oriented comments in English. Run `pnpm check` for formatting, strict TypeScript, lint, unit tests, browser tests, and build.
