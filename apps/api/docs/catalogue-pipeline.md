# Catalogue pipeline design

The catalogue uses PostgreSQL for source identity, structured observations,
entity membership, and published metadata. Celery runs fetch, matching, and
publication jobs. Raw responses and ranking signals have independent lifecycles.

## Source documents and mapping

Archive the response body before JSON decoding or projection. Record a digest,
provider, endpoint, response media type, fetch time, and permitted cache
validators. Omit authorization headers and URL credentials. Keep the exact body
in private storage and reference a shared response when it contains more than
one provider record. A record revision should identify the relevant JSON
pointer or ordered page references. Historical parsed-only revisions remain
replayable at the record level with their capture format identified explicitly.

Store mapper name, version, input revision, and schema version with each
observation. Typed tables own frequent fields and edges. General facts cover
provider-specific extensions. A current-observation pointer selects the
published result of a successful projection transaction. Failed fetches and
mapping attempts retain their audit without replacing a successful observation.

## Identity and relationship read models

An entity has a stable public UUID. Source identities retain their own stable
keys and observation history. A same-entity decision changes an effective
membership record and publishes an audit event. Compatibility checks run before
activation, including entity type, granularity, conflicting verified identifiers
and visibility. Ending a membership rebuilds the affected published outputs.
User records keep their original targets and review history, including records
created while a match was active. Public aliases provide address continuity.

Episode lists use one eligible provider per work and track the coverage of each
collection. Credits fall back by normalized role and deduplicate contributors by
canonical identity. Related work edges prefer higher-priority evidence for the
same canonical target and relation type. Distinct edges can come from multiple
providers. Provider policy and current observation checks run before selection.

## Entity metadata and publication

Only the subject entity is in the metadata generation scope. Related episodes,
credits, characters and works use deterministic catalogue read models. Names
from sources remain available separately from the name chosen for publication.

| Record | Responsibility |
| --- | --- |
| `entity_metadata_revision` | Candidate or approved title, synopsis, and cover per work and language. Stores the exact chosen title, references to the source name and asset, the evidence fingerprint, generator/model versions, and the reviewer. |
| `entity_metadata_citation` | Ordered references to the source descriptions used by a revision, with a content digest for each excerpt. |
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
eligible names, source descriptions, and cover options for one work. The campaign
worker records proposals as drafts. Curators inspect revisions and publish
against the evidence fingerprint:

```sh
uv run python -m scripts.work_metadata show ENTITY_UUID --language en
uv run python -m scripts.work_metadata publish ENTITY_UUID EVIDENCE_HASH --language en
```

Public API and MCP read the same publication. The model never receives third-party
rating or popularity values, episodes, credits, characters, or related works.

## Ranking and migration

Store observations and derived ordering only in the ranking domain. Public
queries may order results by the internal rank and only serialize the entities.
When migrating, validate fresh installs, populated upgrades, replay, split
without data loss, publication rollback, and signal exclusion at every public
surface. Remove replaced storage and compatibility code after the corresponding
reader and writer switch.
