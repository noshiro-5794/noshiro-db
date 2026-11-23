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
Resolution uses effective identity memberships and preserves the underlying evidence. Entity and
field visibility, audience, and spoiler rules govern presentation.

An approved identity match creates an `entity_identity_membership` edge and
an audit event. Entity lifecycle, facts, provider revisions, and user records
retain their existing values. To reverse an edge, run
`uv run python -m scripts.split_match EVENT_ID --reason "Review decision"`
from the API directory. The split re-evaluates the affected fact selections.

## Source archive

The manual Bangumi work sync archives eligible upstream response bodies before
decoding. `ingest.source_document` deduplicates bodies per provider.
`ingest.source_fetch` records each request and `ingest.revision_source` links
the subject revision to the archived response. Earlier revisions and other
import paths currently retain their parsed record payload.

From the API directory, `uv run python -m scripts.replay_source SUBJECT_ID FETCH_ID`
replays the captured subject without provider network access. The replay checks
the endpoint and current revision before applying the mapper.

## Relationship sources

Public relationship queries use eligible current observations. The application
prefers one provider's episode list to keep numbering and specials consistent.
Credits fall back by role. Related works choose the preferred evidence for each
canonical target and relation type, then include distinct edges from other sources.
These choices leave source evidence and episode progress identities intact.

Override the priority order using `RELATIONSHIP_SOURCES` as JSON, for example
`{"episodes":["bangumi","anilist"],"credits":["bangumi","anilist","mal","vndb"]}`.
Omitted lists take their defaults. Visibility and redistribution filters apply
before provider priority.

## Internal ranking

External engagement observations live in `ranking.provider_metric`.
`ranking.entity_rank` holds the derived ordering score. Public listings use it
for ordering and return entity data. Provider scores, vote counts, and comment
counts stay outside the public API, MCP and display inputs.

## Subject metadata

The metadata generator receives current, eligible evidence for a single work.
The internal MCP tools `get_metadata_evidence` and `submit_metadata_draft` share
the validation and draft storage flow. Drafts cite source names, descriptions,
and eligible assets. Publishing checks the input fingerprint against current
evidence before switching the active title, synopsis, and cover selection.
Relations and credits use provider priority independently of the model.

[Catalogue pipeline design](catalogue-pipeline.md)

## AI and provider synchronization

Workers can create structured proposals from source observations and artifacts.
Matching policy and staff review control application to canonical records.
Runs, steps, tool invocations, and claims can be inspected separately.

Synchronization campaigns checkpoint discovery pages and lease work items.
The calendar maintains an active airing board and keeps per-episode airing
facts on the referenced works. The public MCP service exposes catalogue
projections through authenticated, rate-limited read tools.
