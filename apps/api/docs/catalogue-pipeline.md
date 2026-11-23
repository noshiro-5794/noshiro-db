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

| Record | Suggested columns and constraints |
| --- | --- |
| Metadata revision | Stable revision ID, entity ID, language, title, short and full synopsis, cover asset ID, normalized field selections, evidence fingerprint, identity version, generator and policy versions, model and run ID, creation time |
| Metadata evidence | Revision ID, field, citation position, and typed references to a name, description, fact, or media occurrence. Maintain links to its observation and apply field-level policy. |
| Publication | Entity ID and language as the key, revision ID, published time and approving actor. Publish only revisions of the same entity and language. |
| Generation run | Entity ID, language, evidence fingerprint, task and policy versions, status and budget. Capture validation, approvals, retries and costs through the existing harness audit. |

The metadata revision deliberately preserves the text that was published.
Facts, relationships and raw inputs retain their normal source identities.
Rule-generated output uses the same validation and publication boundary.
Publish atomically after rechecking current evidence and identity membership.
If a source is withdrawn, replace or invalidate affected content before it is
served again. Public API and MCP share the same read model.

## Harness and tools

Reuse the agent runtime for budgets, retries, transcripts and structured
proposals. Provide narrowly scoped tools for reading an entity's permitted
evidence, reading validation results, and submitting a draft. The worker and
the internal MCP server share validation and draft persistence. The publication
service owns approval and activation. Pass only current evidence permitted for
AI use to a model and exclude provider engagement metrics and relationship
collections from metadata inputs. Keep model service settings and task rollout
separate from the production automatic matching pause.

## Ranking and migration

Store observations and derived ordering only in the ranking domain. Public
queries may order results by the internal rank and only serialize the entities.
When migrating, validate fresh installs, populated upgrades, replay, split
without data loss, publication rollback, and signal exclusion at every public
surface. Remove replaced storage and compatibility code after the corresponding
reader and writer switch.
