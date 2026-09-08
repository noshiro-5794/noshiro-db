"""Bounded MAL anime import into the source-neutral knowledge graph.

Unlike Bangumi/VNDB full imports, the MAL adapter intentionally imports only
the metadata a weekly board and identity matcher need: stable record, anime
profile, multilingual titles, synopsis, images, and provider facts. Characters,
staff, studios, and relations can be added later by dedicated campaigns without
changing the canonical entity that is created here.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils.text import slugify

from apps.index.models import (
    AnimeProfile,
    Entity,
    EntityName,
    ExternalLink,
    IndexCollection,
    IndexMembership,
    Predicate,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.index.services import (
    entity_resolution_service,
    knowledge_ingestion_service,
)
from apps.sync.providers.contracts import FetchedSourceRecord
from apps.sync.providers.mal import (
    MAL_ANIME_NAMESPACE,
    MAL_SCHEDULE_ITEM_NAMESPACE,
    jikan_client,
)
from apps.sync.services.source_record_service import source_record_service


class MALImportService:
    MAPPER_VERSION = "mal-anime-v1"

    def import_anime(self, mal_id: int) -> Entity:
        if not isinstance(mal_id, int) or isinstance(mal_id, bool) or mal_id <= 0:
            raise ValueError("MAL anime ids must be positive integers.")
        item = jikan_client.fetch_anime_full(mal_id)
        return self._persist_anime(item)

    def import_saved_anime(self, mal_id: int) -> Entity:
        """Import a MAL anime from its already-persisted schedule payload."""
        record = (
            ProviderRecord.objects.filter(
                namespace__provider__slug=MAL_ANIME_NAMESPACE.source.slug,
                namespace__slug=MAL_SCHEDULE_ITEM_NAMESPACE.slug,
                external_id=str(mal_id),
                status=ProviderRecord.Status.ACTIVE,
            )
            .select_related("latest_revision")
            .first()
        )
        if record is None or record.latest_revision is None:
            raise ValueError(
                f"MAL anime {mal_id} has no persisted schedule payload to import."
            )
        payload = record.latest_revision.payload
        if not isinstance(payload, dict) or payload.get("mal_id") != int(mal_id):
            raise ValueError(f"MAL anime {mal_id} payload is inconsistent.")
        return self._persist_anime(payload)

    @transaction.atomic
    def _persist_anime(self, item: dict[str, Any]) -> Entity:
        external_id = str(item["mal_id"])
        recorded = source_record_service.record(
            namespace_spec=MAL_ANIME_NAMESPACE,
            fetched=FetchedSourceRecord(
                external_id=external_id,
                payload=item,
                canonical_url=f"https://myanimelist.net/anime/{external_id}",
                schema_version="jikan-v4-full",
                mapper_version=self.MAPPER_VERSION,
            ),
        )
        observation = knowledge_ingestion_service.record_observation(
            provider_record=recorded.record,
            mapper="mal.anime",
            mapper_version=self.MAPPER_VERSION,
            normalized_data=item,
            schema_name="index.work",
            schema_version="1",
        )
        entity = knowledge_ingestion_service._resolve_or_create_entity(
            provider_record=recorded.record,
            kind=Entity.Kind.WORK,
            audience=Entity.Audience.GENERAL,
        )
        work, _ = Work.objects.update_or_create(
            entity=entity,
            defaults={"work_type": Work.WorkType.ANIME},
        )
        AnimeProfile.objects.update_or_create(
            work=work,
            defaults={
                "format": str(item.get("type") or ""),
                "episode_count": self._as_int(item.get("episodes")),
            },
        )
        knowledge_ingestion_service._upsert_provider_representation(
            provider_record=recorded.record,
            entity=entity,
            representation_method=ProviderRepresentation.Method.PROVIDER,
        )
        self._upsert_names(
            entity=entity,
            record=recorded.record,
            observation=observation,
            item=item,
        )
        self._upsert_description(
            entity=entity,
            record=recorded.record,
            observation=observation,
            item=item,
        )
        self._upsert_media(
            entity=entity,
            record=recorded.record,
            observation=observation,
            item=item,
        )
        self._upsert_external_link(
            entity=entity,
            record=recorded.record,
            observation=observation,
            external_id=external_id,
        )
        self._upsert_facts(
            entity=entity,
            observation=observation,
            item=item,
        )
        self._ensure_anime_membership(entity)
        return entity_resolution_service.resolve(entity)

    @staticmethod
    def _as_int(value: Any) -> int | None:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    @staticmethod
    def _upsert_names(*, entity, record, observation, item) -> None:
        names: list[EntityName] = []
        seen: set[tuple[str, str, str]] = set()

        def add(*, text: str, language: str, kind: str) -> None:
            key = (text, language, kind)
            if not text or key in seen:
                return
            seen.add(key)
            names.append(
                EntityName(
                    entity=entity,
                    provider_record=record,
                    observation=observation,
                    text=text[:256],
                    language=language,
                    kind=kind,
                )
            )

        for title in item.get("titles") or []:
            if not isinstance(title, dict):
                continue
            text = title.get("title")
            title_type = title.get("type")
            if isinstance(text, str) and isinstance(title_type, str):
                if title_type.lower() == "japanese":
                    add(text=text, language="ja", kind=EntityName.Kind.ORIGINAL)
                elif title_type.lower() == "english":
                    add(text=text, language="en", kind=EntityName.Kind.OFFICIAL)
                else:
                    add(text=text, language="", kind=EntityName.Kind.ROMANIZED)
        english = item.get("title_english")
        if isinstance(english, str):
            add(text=english, language="en", kind=EntityName.Kind.OFFICIAL)
        japanese = item.get("title_japanese")
        if isinstance(japanese, str):
            add(text=japanese, language="ja", kind=EntityName.Kind.ORIGINAL)
        for synonym in item.get("title_synonyms") or []:
            if isinstance(synonym, str):
                add(text=synonym, language="", kind=EntityName.Kind.ALIAS)
        EntityName.objects.bulk_create(names, ignore_conflicts=True)

    @staticmethod
    def _upsert_description(*, entity, record, observation, item) -> None:
        synopsis = item.get("synopsis")
        if isinstance(synopsis, str) and synopsis.strip():
            knowledge_ingestion_service._upsert_description(
                entity=entity,
                provider_record=record,
                observation=observation,
                text=synopsis,
            )

    @staticmethod
    def _upsert_media(*, entity, record, observation, item) -> None:
        images = item.get("images") or {}
        jpg = images.get("jpg") if isinstance(images, dict) else {}
        webp = images.get("webp") if isinstance(images, dict) else {}
        candidates = (
            (
                "poster",
                jpg.get("large_image_url") if isinstance(jpg, dict) else None,
                webp.get("large_image_url") if isinstance(webp, dict) else None,
            ),
            (
                "thumbnail",
                jpg.get("small_image_url") if isinstance(jpg, dict) else None,
                webp.get("small_image_url") if isinstance(webp, dict) else None,
            ),
        )
        for purpose, jpg_url, webp_url in candidates:
            url = webp_url or jpg_url
            if not isinstance(url, str) or not url:
                continue
            knowledge_ingestion_service._upsert_media(
                entity=entity,
                provider_record=record,
                observation=observation,
                original=url if purpose == "poster" else "",
                thumbnail=url if purpose == "thumbnail" else "",
            )

    @staticmethod
    def _upsert_external_link(
        *,
        entity,
        record,
        observation,
        external_id: str,
    ) -> None:
        url = f"https://myanimelist.net/anime/{external_id}"
        ExternalLink.objects.get_or_create(
            entity=entity,
            url=url,
            provider_record=record,
            observation=observation,
            defaults={"label": "MyAnimeList", "link_type": "mal"},
        )

    @staticmethod
    def _upsert_facts(*, entity, observation, item) -> None:
        aired = item.get("aired") if isinstance(item.get("aired"), dict) else {}
        duration = item.get("duration")
        duration_minutes = None
        if isinstance(duration, str):
            match = re.fullmatch(r"(\d+) min per ep", duration.strip())
            if match:
                duration_minutes = int(match.group(1))
        broadcast = (
            item.get("broadcast") if isinstance(item.get("broadcast"), dict) else {}
        )
        candidates = {
            "mal-status": item.get("status"),
            "mal-type": item.get("type"),
            "mal-season": item.get("season"),
            "mal-year": item.get("year"),
            "mal-score": item.get("score"),
            "mal-rank": item.get("rank"),
            "mal-popularity": item.get("popularity"),
            "mal-members": item.get("members"),
            "mal-favourites": item.get("favorites"),
            "episode-count": item.get("episodes"),
            "duration-minutes": duration_minutes,
            "broadcast-day": broadcast.get("day"),
            "broadcast-time": broadcast.get("time"),
            "broadcast-timezone": broadcast.get("timezone"),
            "release-date": _parse_iso_date(aired.get("from")),
            "end-date": _parse_iso_date(aired.get("to")),
        }
        for slug, value in candidates.items():
            if value is None or value == "":
                continue
            value_type = Predicate.ValueType.STRING
            if slug in {"release-date", "end-date"}:
                value_type = Predicate.ValueType.DATE
            elif isinstance(value, bool):
                value_type = Predicate.ValueType.BOOLEAN
            elif isinstance(value, (int, float, Decimal)):
                value_type = Predicate.ValueType.NUMBER
            knowledge_ingestion_service.record_fact(
                entity=entity,
                observation=observation,
                slug=slug,
                name=slug.replace("-", " ").title(),
                value=value,
                value_type=value_type,
                json_pointer=f"/{slugify(slug)}",
            )

    @staticmethod
    def _ensure_anime_membership(entity: Entity) -> None:
        collection, _ = IndexCollection.objects.get_or_create(
            slug="anime",
            defaults={"name": "Anime"},
        )
        IndexMembership.objects.update_or_create(
            collection=collection,
            entity=entity,
            defaults={
                "listing_state": IndexMembership.State.LISTED,
                "inclusion_reason": "MAL anime",
            },
        )


mal_import_service = MALImportService()


def _parse_iso_date(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC)
    return parsed.date().isoformat()
