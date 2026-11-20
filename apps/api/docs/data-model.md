# Catalogue data model

## Identity

An entity has a stable UUID, lifecycle, visibility, and redirect target. A
work represents a creative work, while a release represents an edition with
a particular platform, language, region, or distribution. Episodes,
characters, people, and organizations can be linked to the same catalogue.

Sequels and independent seasons may be distinct works. Localized titles and
editions can belong to the same work. Typed relationships cover recurring
edges, while facts capture less common source attributes.

## Provenance and projections

```text
Provider record → immutable revision → mapping run → observation
        │                                             │
        └──── representation → entity ← facts and relations
```

Provider records identify upstream objects. Revisions preserve the fetched
payload, observations record mapper output, and current-observation pointers
select the evidence used by read models. Names retain language, script, and
region. Partial dates retain precision. Metrics retain provider and observation
time.

Display projections select summaries, names, and artwork for the public API.
Resolution uses redirects and preserves the underlying evidence. Entity and
field visibility, audience, and spoiler rules govern presentation.

## AI and provider synchronization

Workers can create structured proposals from source observations and artifacts.
Matching policy and staff review control application to canonical records.
Runs, steps, tool invocations, and claims can be inspected separately.

Synchronization campaigns checkpoint discovery pages and lease work items.
The calendar maintains an active airing board and keeps per-episode airing
facts on the referenced works. The public MCP service exposes catalogue
projections through authenticated, rate-limited read tools.
