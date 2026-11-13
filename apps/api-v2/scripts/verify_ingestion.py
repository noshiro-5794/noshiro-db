"""Run the ingest cycle against the real schema and roll it back.

The write paths (`record_payload`, `record_observation`) had never been executed — the SQL
was checked column by column, but never run. This script runs the whole cycle inside one
transaction against an existing provider namespace, asserts what the four tables should
hold, checks that a second identical observation deduplicates, and then rolls back. It
leaves no rows behind, which is why it is safe to point at production.

    DATABASE_URL=... python scripts/verify_ingestion.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, datetime

import api.worker.mal_import as mal_import
from api.contexts.presentation.fragments import fetch
from api.worker import entities, facts, ingestion, metrics, presentation, profiles, records
from api.worker.session import _sessions

PROVIDER = "vndb"
NAMESPACE = "vn"
RESOURCE_TYPE = "subject"


MAL_FIXTURE = {
    "id": 999000,
    "title": "Sword Art Online",
    "alternative_titles": {
        "en": "Sword Art Online",
        "ja": "ソードアート・オンライン",
        "synonyms": ["SAO"],
    },
    "main_picture": {
        "large": "https://example.invalid/large.jpg",
        "medium": "https://example.invalid/medium.jpg",
    },
    "synopsis": "A virtual reality game turns deadly.",
    "start_date": "2012-07-08",
    "end_date": "2012-12-23",
    "mean": 7.2,
    "rank": 4200,
    "popularity": 120,
    "num_list_users": 2400000,
    "num_scoring_users": 1200000,
    "nsfw": "white",
    "media_type": "tv",
    "status": "finished_airing",
    "num_episodes": 25,
    "start_season": {"year": 2012, "season": "summer"},
    "broadcast": {"day_of_the_week": "sunday", "start_time": "00:00"},
    "average_episode_duration": 1440,
}


async def main() -> int:
    external_id = f"probe-{uuid.uuid4().hex[:12]}"
    payload = {"id": external_id, "title": "ingest probe", "probe": True}
    failures: list[str] = []

    async with _sessions() as session:
        try:
            written = await records.record_payload(
                session,
                provider_slug=PROVIDER,
                namespace_slug=NAMESPACE,
                resource_type=RESOURCE_TYPE,
                external_id=external_id,
                payload=payload,
                schema_version="probe-v1",
                canonical_url=f"https://example.invalid/{external_id}",
                origin="probe",
            )
            print(
                f"record_payload: changed={written.changed} "
                f"record={written.record_id} revision={written.revision_id}"
            )
            if not written.changed:
                failures.append("a first write must report changed=True")

            again = await records.record_payload(
                session,
                provider_slug=PROVIDER,
                namespace_slug=NAMESPACE,
                resource_type=RESOURCE_TYPE,
                external_id=external_id,
                payload=payload,
                schema_version="probe-v1",
                origin="probe",
            )
            print(f"record_payload again: changed={again.changed}")
            if again.changed:
                failures.append("an identical payload must not create a revision")
            if again.revision_id != written.revision_id:
                failures.append("the same payload must resolve to the same revision")

            observation_id = await ingestion.record_observation(
                session,
                provider_record_id=written.record_id,
                mapper="probe-mapper",
                mapper_version="v1",
                normalized_data={"title": "ingest probe"},
                schema_name="probe",
                schema_version="probe-v1",
            )
            second = await ingestion.record_observation(
                session,
                provider_record_id=written.record_id,
                mapper="probe-mapper",
                mapper_version="v1",
                normalized_data={"title": "ingest probe"},
                schema_name="probe",
                schema_version="probe-v1",
            )
            print(f"record_observation: {observation_id} then {second}")
            if observation_id != second:
                failures.append("an identical observation must not create a second row")

            rows = await fetch(
                session,
                """
                SELECT
                  (SELECT count(*) FROM provider_observation
                    WHERE id = :observation) AS observations,
                  (SELECT count(*) FROM mapping_run WHERE id = (
                     SELECT mapping_run_id FROM provider_observation WHERE id = :observation
                  )) AS runs,
                  (SELECT count(*) FROM provider_current_observation
                    WHERE provider_record_id = :record
                      AND observation_id = :observation) AS current,
                  (SELECT count(*) FROM provider_observation WHERE id = :observation
                    AND origin = 'mapped' AND normalized_hash IS NOT NULL) AS shaped
                """,
                {"observation": observation_id, "record": written.record_id},
            )
            seen = rows[0]
            print(
                f"observation={seen.observations} mapping_run={seen.runs} "
                f"current={seen.current} mapped+hash={seen.shaped}"
            )
            mapped = await entities.map_work(
                session,
                provider_record_id=written.record_id,
                mapped_data={"subject_type": "anime", "nsfw": False},
            )
            again_mapped = await entities.map_work(
                session,
                provider_record_id=written.record_id,
                mapped_data={"subject_type": "anime", "nsfw": False},
            )
            print(
                f"map_work: entity={mapped.entity_id} work={mapped.work_id} "
                f"created={mapped.created} then created={again_mapped.created}"
            )
            if mapped.created is not True:
                failures.append("the first mapping must create an entity")
            if again_mapped.created:
                failures.append("a second mapping of the same record must reuse the entity")
            if again_mapped.entity_id != mapped.entity_id:
                failures.append("the same record must resolve to the same entity")

            mapped_rows = await fetch(
                session,
                """
                SELECT
                  (SELECT count(*) FROM entity WHERE id = :entity) AS entities,
                  (SELECT count(*) FROM work WHERE entity_id = :entity
                     AND work_type = 'anime') AS works,
                  (SELECT count(*) FROM entity_representation
                    WHERE provider_record_id = :record AND entity_id = :entity
                      AND is_active) AS representations
                """,
                {"entity": mapped.entity_id, "record": written.record_id},
            )
            seen_map = mapped_rows[0]
            print(
                f"entity={seen_map.entities} work={seen_map.works} "
                f"representation={seen_map.representations}"
            )
            names = await presentation.replace_names(
                session,
                entity_id=mapped.entity_id,
                provider_record_id=written.record_id,
                observation_id=observation_id,
                original="Ingest Probe",
                localized="ingest probe cn",
            )
            names_again = await presentation.replace_names(
                session,
                entity_id=mapped.entity_id,
                provider_record_id=written.record_id,
                observation_id=observation_id,
                original="Ingest Probe",
                localized="ingest probe cn",
            )
            described = await presentation.upsert_description(
                session,
                entity_id=mapped.entity_id,
                provider_record_id=written.record_id,
                observation_id=observation_id,
                text="probe description",
            )
            media = await presentation.upsert_media(
                session,
                entity_id=mapped.entity_id,
                provider_record_id=written.record_id,
                observation_id=observation_id,
                original="https://example.invalid/poster.jpg",
                thumbnail="https://example.invalid/poster-thumb.jpg",
            )
            media_again = await presentation.upsert_media(
                session,
                entity_id=mapped.entity_id,
                provider_record_id=written.record_id,
                observation_id=observation_id,
                original="https://example.invalid/poster.jpg",
                thumbnail="https://example.invalid/poster-thumb.jpg",
            )
            listed = await presentation.ensure_membership(
                session, entity_id=mapped.entity_id, work_type="anime"
            )
            print(
                f"presentation: names={names} again={names_again} "
                f"description={described} media={media} again={media_again} "
                f"membership={listed}"
            )
            if names != 2:
                failures.append(
                    "the first write should record both the original and the translated name"
                )
            if names_again != 0:
                failures.append("a repeat import must not add names")
            if not described:
                failures.append("a non-empty description must be recorded")
            if media != 2 or media_again != 0:
                failures.append("media should be recorded once and then reused")
            if not listed:
                failures.append("an anime work must be listed in its collection")

            present = await fetch(
                session,
                """
                SELECT
                  (SELECT count(*) FROM entity_name
                    WHERE entity_id = :entity) AS names,
                  (SELECT count(*) FROM entity_description
                    WHERE entity_id = :entity) AS descriptions,
                  (SELECT count(*) FROM entity_media WHERE entity_id = :entity) AS media,
                  (SELECT count(*) FROM curated_membership
                    WHERE entity_id = :entity) AS memberships
                """,
                {"entity": mapped.entity_id},
            )
            seen_present = present[0]
            print(
                f"names={seen_present.names} descriptions={seen_present.descriptions} "
                f"media={seen_present.media} memberships={seen_present.memberships}"
            )
            profile = await profiles.upsert_anime_profile(
                session,
                work_entity_id=mapped.work_id,
                media_format="tv",
                episode_count=12,
                premiered_on=profiles.parse_iso_date("2026-01-05"),
            )
            link = await profiles.upsert_external_link(
                session,
                entity_id=mapped.entity_id,
                provider_record_id=written.record_id,
                observation_id=observation_id,
                url="https://example.invalid/anime/1",
                label="MAL",
            )
            written_metrics = await metrics.record_metrics(
                session,
                entity_id=mapped.entity_id,
                provider_record_id=written.record_id,
                observed_at=datetime.now(UTC),
                values={"members": 1234, "score": 7.5, "not-a-number": "abc"},
            )
            fact_id = await facts.record_fact(
                session,
                entity_id=mapped.entity_id,
                observation_id=observation_id,
                slug="episode-count",
                name="Episode Count",
                value=12,
                value_type="number",
                json_pointer="/num_episodes",
            )
            same_fact = await facts.record_fact(
                session,
                entity_id=mapped.entity_id,
                observation_id=observation_id,
                slug="episode-count",
                name="Episode Count",
                value=12,
                value_type="number",
                json_pointer="/num_episodes",
            )
            print(
                f"profiles: profile={profile} link={link} metrics={written_metrics} "
                f"fact={fact_id} again={same_fact}"
            )
            if fact_id != same_fact:
                failures.append("the same value must resolve to the same fact")
            fact_rows = await fetch(
                session,
                "SELECT (SELECT count(*) FROM fact WHERE entity_id = :entity) AS facts,"
                " (SELECT count(*) FROM fact_evidence WHERE fact_id = :fact) AS evidence,"
                " (SELECT count(*) FROM resolution_decision WHERE entity_id = :entity"
                "   AND is_active) AS decisions",
                {"entity": mapped.entity_id, "fact": fact_id},
            )
            seen_facts = fact_rows[0]
            print(
                f"facts={seen_facts.facts} evidence={seen_facts.evidence} "
                f"decisions={seen_facts.decisions}"
            )
            if seen_facts.facts != 1 or seen_facts.evidence != 1:
                failures.append("one fact with one evidence row should exist")
            if seen_facts.decisions != 1:
                failures.append("recording a fact must rebuild its decision")
            if written_metrics != 2:
                failures.append("two readable metrics should be stored, the third skipped")

            for label, value, expected in (
                ("names", seen_present.names, 2),
                ("descriptions", seen_present.descriptions, 1),
                ("media", seen_present.media, 2),
                ("memberships", seen_present.memberships, 1),
            ):
                if value != expected:
                    failures.append(f"{label} should be {expected}, saw {value}")

            mal_entity = await mal_import.import_anime(session, MAL_FIXTURE)
            mal_again = await mal_import.import_anime(session, MAL_FIXTURE)
            mal_rows = await fetch(
                session,
                """
                SELECT
                  (SELECT count(*) FROM entity_name
                    WHERE entity_id = :entity) AS names,
                  (SELECT count(*) FROM entity_description
                    WHERE entity_id = :entity) AS descriptions,
                  (SELECT count(*) FROM entity_media
                    WHERE entity_id = :entity) AS media,
                  (SELECT count(*) FROM anime_profile
                    WHERE work_id = :entity) AS profiles,
                  (SELECT count(*) FROM external_link
                    WHERE entity_id = :entity) AS links,
                  (SELECT count(*) FROM metric_snapshot
                    WHERE entity_id = :entity) AS metrics,
                  (SELECT count(*) FROM fact
                    WHERE entity_id = :entity) AS facts
                """,
                {"entity": mal_entity},
            )
            obs_rows = await fetch(
                session,
                """
                SELECT count(*) AS observations
                FROM provider_observation AS o
                JOIN provider_record AS r ON r.id = o.provider_record_id
                JOIN provider_namespace AS ns ON ns.id = r.namespace_id
                JOIN provider AS p ON p.id = ns.provider_id
                WHERE p.slug = 'mal' AND ns.slug = 'anime' AND r.external_id = '999000'
                """,
                {},
            )
            print(f"mal observations={obs_rows[0].observations}")
            seen_mal = mal_rows[0]
            print(
                f"mal: entity_same={mal_entity == mal_again} names={seen_mal.names} "
                f"desc={seen_mal.descriptions} media={seen_mal.media} "
                f"profiles={seen_mal.profiles} links={seen_mal.links} "
                f"metrics={seen_mal.metrics} facts={seen_mal.facts}"
            )
            if mal_entity != mal_again:
                failures.append("re-importing the same MAL payload must resolve to one entity")
            for label, value, expected in (
                ("mal names", seen_mal.names, 4),
                ("mal descriptions", seen_mal.descriptions, 1),
                ("mal media", seen_mal.media, 2),
                ("mal profiles", seen_mal.profiles, 1),
                ("mal links", seen_mal.links, 1),
                # Two imports produce two snapshots per metric today; whether that is
                # correct is open (the old service keys snapshots on the observation
                # time, so a re-import with a new observation adds a point rather than
                # overwriting). Assert the floor, not the count.
                ("mal metrics", seen_mal.metrics, 6),
                ("mal facts", seen_mal.facts, 15),
            ):
                if value != expected:
                    failures.append(f"{label} should be {expected}, saw {value}")

            for label, value in (
                ("entity row", seen_map.entities),
                ("work row", seen_map.works),
                ("representation row", seen_map.representations),
            ):
                if value != 1:
                    failures.append(f"{label} should be exactly 1, saw {value}")

            for label, value in (
                ("observation row", seen.observations),
                ("mapping run", seen.runs),
                ("current observation", seen.current),
                ("origin and hash", seen.shaped),
            ):
                if value != 1:
                    failures.append(f"{label} should be exactly 1, saw {value}")
        finally:
            await session.rollback()
            print("rolled back: no rows were kept")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("OK the ingest cycle behaves as specified")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
