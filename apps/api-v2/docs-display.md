# The display layer

What a page shows is a decision, not a row: a title chosen among variants, a
description that may be rewritten, a cover picked among candidates. That decision
now has a home — `entity_display_profile` (revision `0002_display_profile`) — and
an input.

## Input: the bundle

`presentation/bundle.py` builds what the generator receives. It is deliberately
smaller than the detail document and bounded:

| Part | Bound | Carries |
|---|---|---|
| `names` | 20 | id, text, language, script, kind, official/original flags |
| `descriptions` | 3 | id, language, text (1,500 chars), official flag |
| `fields` | all resolved | predicate, value, fact id, confidence, up to 2 alternates |
| `credits` | 20 | role, credited as, contributor id |
| `relations` | 20 | relation type, target id |
| `media` | 6 | url, purpose, safety |

Signals are absent by construction: scores, ranks and vote counts are internal and
must never reach a page.

```bash
DATABASE_URL=... uv run python -m scripts.bundle <entity-id> --language ja
```

Sample, for a merged work with 18 names: 18 fields, 4 credits, 4 relations,
`input_hash` stable across two runs.

## Flow

```
bundle → generator (rules or agent) → submit → validator → draft → active
```

- **Generator**: may rewrite `description_text`; every other value must cite an
  id from the bundle (`title_name_id`, `field_choices[].fact_id`,
  `cover_asset_id`).
- **Validator** (deterministic code, not the model): every cited id exists and
  belongs to the entity; numbers and dates in a rewritten text appear in a cited
  fact; the language matches; the length is sane.
- **Draft**: the row lands with `state = 'draft'` and the bundle's `input_hash`,
  so rerunning the same input updates rather than duplicates.
- **Active**: one row per entity and language, enforced by
  `uq_display_profile_active`; a rejected draft never replaces a live page.

## First run

```bash
DATABASE_URL=... uv run python -m scripts.display <entity-id> --apply
```

Seven drafts over six entities, every one valid. One entity has two drafts
because the bundle changed between runs — the media query gained asset ids, the
`input_hash` changed with it, and a different input earns a different draft. That
is the hash doing its job, not a duplicate.

Rerunning an entity whose bundle did not change leaves the row count untouched:
`ON CONFLICT (entity_id, language, input_hash)` updates in place.

## What is still missing

- the validator and the generator themselves;
- a reader that serves the `active` row with a fallback to today's projector;
- a comparison of the two readers, before any page changes.
