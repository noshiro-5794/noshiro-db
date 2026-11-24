# Catalogue pipeline design

The catalogue uses PostgreSQL for source identity, structured observations,
entity membership, and published metadata. Celery runs fetching, matching, and metadata generation. Publication is a
separate reviewed step. Raw responses and ranking signals have independent lifecycles.

## Source documents and mapping

The worker commits each eligible response body to `ingest.source_document`
before JSON decoding. Document bytes are deduplicated per provider. Separate
fetch events record the endpoint path, HTTP method, status, media type, time,
and a request fingerprint. Credentials, request bodies, and URL query values
stay outside the archive. `ingest.revision_source` traces each parsed revision
to the relevant response and JSON location.

Catalogue fetches and complete manual Bangumi syncs retain a batch identifier.
Replay runs the provider parser and mapper with archived responses, including
paginated follow-ups. It previews projections in a rolled-back transaction by
default. Applying a batch requires current, active source revisions. Historical
records created before original-response retention retain their parsed input.

Mapper runs reference a parsed revision and its versioned observation. Typed
tables hold names, people, episodes, credits, and work relationships. A
current-observation pointer identifies the selected projection. When the
observation is identical to its parsed revision, the mapping run references
that revision's payload. Only distinct projection data is stored on the
observation.

## Identity and relationship read models

An entity has a stable public UUID. Source identities retain their own stable
keys and observation history. A same-entity decision changes an effective
membership record and publishes an audit event. Compatibility checks run before
activation, including entity type, granularity, conflicting verified identifiers
and visibility. Ending a membership rebuilds the affected published outputs.
User records keep their original targets and review history, including records
created while a match was active. Public aliases provide address continuity.

Episode lists use one eligible provider per work, including that provider's
titles, ordering, and episode fields. A complete collection takes precedence
over an unknown or partial one. Within the same coverage level, the configured
provider order applies. Credits fall back by normalized role and deduplicate contributors by
canonical identity. Related work edges prefer higher-priority evidence for the
same canonical target and relation type. Distinct edges can come from multiple
providers. Provider policy and current observation checks run before selection.
A staff decision grouping two distinct works creates a same-season relation.
Published collection slugs retain their existing navigation targets.

Credit roles and relationship types have stable vocabulary keys. The credit
read model localizes known roles in Chinese, Japanese, and English and retains
the source wording for unknown roles. The Web app localizes relationship keys.
Raw credits and relationship evidence remain available for replay and review.
Scoped `taxonomy_alias` entries support reviewed AI vocabulary normalization.
Model proposals enter the claim audit trail before review. The source mapper
preserves platform text, original role text, and source field labels.

## Entity metadata and publication

Only the subject entity is in the metadata generation scope. Related episodes,
credits, characters and works use deterministic catalogue read models. Names
from sources remain available separately from the name chosen for publication.

| Record | Responsibility |
| --- | --- |
| `entity_metadata_revision` | Candidate or approved title, synopsis, and cover per work and language. Stores the exact chosen title, references to the source name and asset, the evidence fingerprint, generator/model versions, and the reviewer. |
| `entity_metadata_citation` | Ordered references to the source descriptions used by a revision, with a content digest for each excerpt. |
| `entity_metadata_field_choice` | Reviewed labels and references to eligible work field evidence for animation and visual novels. |
| `entity_metadata_publication` | One current revision per work and language. A composite foreign key enforces the publication scope. |
| `agent_step` and `ai_run` | Generation status, model, usage, and outcome. Worker-generated revisions reference their generating step. |

Approval checks the evidence fingerprint and current identity within the publication
transaction. The previous approved revision remains available for review. Each
public read rechecks current source evidence and policy before serving a revision.
The site uses deterministic name, description, and cover selection when a published
value becomes ineligible.

## Harness and tools

The internal MCP tools `get_metadata_evidence` and `submit_metadata_draft` use
the same scope and validation as the campaign worker. Model inputs contain
eligible names, source descriptions, cover options, and display field evidence for one work. The campaign
worker records proposals as drafts. Curators inspect proposals and publish an immutable draft revision. Publication
verifies that its evidence fingerprint is still current.

```sh
uv run python -m scripts.work_metadata show ENTITY_UUID --language en
uv run python -m scripts.work_metadata publish ENTITY_UUID REVISION_ID --language en
```

Public API and MCP read the same publication. The model never receives third-party
rating or popularity values, user tags, episode records, character records, or related works. Source infobox credit text can appear as a cited work field.

[Work metadata fields and refresh coverage](work-metadata-fields.md)

## Ranking and migration

The ranking schema holds external engagement observations and derived ordering.
Catalogue listings and the weekly calendar use internal ordering. Their public
responses serialize the catalogue data and omit raw signals and derived rank.
The active broadcast board uses provider observations and rule-based selection.
When migrating, validate fresh installs, populated upgrades, replay, split
without data loss, publication rollback, and signal exclusion at every public
surface. Remove replaced storage and compatibility code after the corresponding
reader and writer switch.
