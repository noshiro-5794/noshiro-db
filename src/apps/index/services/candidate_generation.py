"""Read-only-first candidate generation for cross-provider work identity.

Providers without shared official identifiers (AniList only exposes MAL IDs,
which Bangumi does not carry) need title/date evidence before an AI evaluator
can decide whether two entities are the same real work. This service searches
the target provider by each source entity name and creates idempotent
``MatchCandidate`` rows with ``title_similarity`` evidence. MAL is supported as
a source provider even though its strongest identity bridge (AniList ``idMal``)
is handled deterministically by :mod:`apps.index.services.mal_identity`.
"""

from __future__ import annotations

from typing import Any

from django.db import connection, transaction

from apps.index.models import MatchCandidate, MatchEvidence


class ProviderCandidateService:
    POLICY_VERSION = "title-similarity-v1"

    def generate_candidates(
        self,
        *,
        source_provider: str = "anilist",
        source_namespace: str = "anime",
        target_provider: str = "bangumi",
        target_namespace: str = "subject",
        min_similarity: float = 0.6,
        top_k: int = 5,
        create: bool = True,
    ) -> dict[str, Any]:
        """Match active source anime works against target anime subject works."""
        source_names = self._source_names(
            provider_slug=source_provider,
            namespace_slug=source_namespace,
        )
        policy_version = self._policy_version(source_provider, target_provider)
        summary = {
            "source_entities": 0,
            "source_provider": source_provider,
            "target_provider": target_provider,
            "anilist_entities": 0,
            "candidates_created": 0,
            "created_ids": [],
            "pairs": [],
        }
        entities: dict[str, list[dict[str, Any]]] = {}
        for name_row in source_names:
            entities.setdefault(str(name_row["entity_id"]), []).append(name_row)
        for entity_id, names in entities.items():
            summary["source_entities"] += 1
            if source_provider == "anilist":
                summary["anilist_entities"] += 1
            best: dict[str, dict[str, Any]] = {}
            for name in names:
                for match in self._target_matches(
                    name=name["text"],
                    provider_slug=target_provider,
                    namespace_slug=target_namespace,
                    min_similarity=min_similarity,
                    top_k=top_k,
                ):
                    key = str(match["entity_id"])
                    if key not in best or match["similarity"] > best[key]["similarity"]:
                        best[key] = {
                            "entity_id": match["entity_id"],
                            "text": match["text"],
                            "similarity": match["similarity"],
                            "source_text": name["text"],
                        }
            for match in best.values():
                summary["pairs"].append(
                    {
                        "source_entity": str(entity_id),
                        "source_text": match["source_text"],
                        "target_entity": str(match["entity_id"]),
                        "target_text": match["text"],
                        "similarity": round(float(match["similarity"]), 4),
                    }
                )
                if not create:
                    continue
                created = self._create_candidate(
                    source_entity_id=entity_id,
                    target_entity_id=match["entity_id"],
                    policy_version=policy_version,
                    source_text=match["source_text"],
                    target_text=match["text"],
                    similarity=float(match["similarity"]),
                    provider_pair=f"{source_provider}:{target_provider}",
                )
                if created is not None:
                    summary["candidates_created"] += 1
                    summary["created_ids"].append(created)
        return summary

    def generate_mal_bangumi_candidates(
        self,
        *,
        min_similarity: float = 0.6,
        top_k: int = 5,
        create: bool = True,
    ) -> dict[str, Any]:
        return self.generate_candidates(
            source_provider="mal",
            source_namespace="anime",
            target_provider="bangumi",
            target_namespace="subject",
            min_similarity=min_similarity,
            top_k=top_k,
            create=create,
        )

    @staticmethod
    def _policy_version(source_provider: str, target_provider: str) -> str:
        if (source_provider, target_provider) == ("anilist", "bangumi"):
            return ProviderCandidateService.POLICY_VERSION
        return f"title-similarity-{source_provider}-{target_provider}-v1"

    @staticmethod
    def _source_names(
        *,
        provider_slug: str,
        namespace_slug: str,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT e.id, en.text
                FROM index_entity e
                JOIN provider_representation pr
                  ON pr.entity_id = e.id AND pr.is_active
                JOIN provider_record rec ON rec.id = pr.provider_record_id
                JOIN provider_namespace pn
                  ON pn.id = rec.namespace_id AND pn.slug = %s
                JOIN provider p ON p.id = pn.provider_id AND p.slug = %s
                JOIN entity_name en ON en.entity_id = e.id
                WHERE btrim(en.text) <> ''
                ORDER BY e.id, en.text
                """,
                [namespace_slug, provider_slug],
            )
            rows = cursor.fetchall()
        return [{"entity_id": row[0], "text": row[1]} for row in rows]

    @staticmethod
    def _target_matches(
        *,
        name: str,
        provider_slug: str,
        namespace_slug: str,
        min_similarity: float,
        top_k: int,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT en.entity_id, en.text, similarity(en.text, %s) AS sim
                FROM entity_name en
                JOIN provider_representation pr
                  ON pr.entity_id = en.entity_id AND pr.is_active
                JOIN provider_record rec ON rec.id = pr.provider_record_id
                JOIN provider_namespace pn
                  ON pn.id = rec.namespace_id AND pn.slug = %s
                JOIN provider p ON p.id = pn.provider_id AND p.slug = %s
                JOIN work w ON w.entity_id = en.entity_id
                WHERE btrim(en.text) <> ''
                  AND w.work_type = 'anime'
                  AND similarity(en.text, %s) >= %s
                ORDER BY sim DESC, en.entity_id
                LIMIT %s
                """,
                [name, namespace_slug, provider_slug, name, min_similarity, top_k],
            )
            return [
                {
                    "entity_id": row[0],
                    "text": row[1],
                    "similarity": row[2],
                }
                for row in cursor.fetchall()
            ]

    @staticmethod
    @transaction.atomic
    def _create_candidate(
        *,
        source_entity_id,
        target_entity_id,
        policy_version: str,
        source_text: str,
        target_text: str,
        similarity: float,
        provider_pair: str,
    ) -> Any:
        left, right = sorted(
            (source_entity_id, target_entity_id),
            key=lambda value: str(value),
        )
        candidate, created = MatchCandidate.objects.get_or_create(
            left_entity_id=left,
            right_entity_id=right,
            policy_version=policy_version,
            defaults={
                "score": similarity,
                "runner_up_margin": 0,
                "status": MatchCandidate.Status.PENDING,
                "hard_conflicts": [],
            },
        )
        if not created:
            return None
        MatchEvidence.objects.create(
            candidate=candidate,
            evidence_type="title_similarity",
            value={
                "provider_pair": provider_pair,
                "source_text": source_text,
                "target_text": target_text,
                "similarity": round(similarity, 4),
            },
            weight=similarity,
        )
        return str(candidate.pk)


provider_candidate_service = ProviderCandidateService()
