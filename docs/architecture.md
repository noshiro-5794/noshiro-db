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
- `features` is for domain logic such as auth, subjects, library, search, calendar, social, docs, and profile.
- `shared/ui` is for reusable UI primitives without domain ownership.
- `pages` compose features into routes.

## API Layer

Feature APIs live next to their domain:

- `features/auth/api.ts`
- `features/subjects/api.ts`
- `features/library/api.ts`
- `features/social/api.ts`
- `features/sync/api.ts`

React Query options are defined per feature so pages can stay focused on composition and user flow.
