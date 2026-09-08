"""Agent-based recall for Bangumi works that lack any MAL candidate.

The candidate generator matches MAL -> Bangumi through normalized SQL, which
misses titles whose scripts differ by width, spacing, or punctuation. For
unresolved Bangumi works this service runs a bounded retrieval agent instead:
it may search the internal knowledge graph and the official MAL API, then
returns a real MAL id or abstains. A found result is imported (when needed),
persisted as a pending candidate with agent evidence, and optionally handed to
the existing adjudicator for a precise bind/group/reject decision.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Literal

from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, Field

from apps.ai.models import AgentRun
from apps.ai.runtime.agent_loop import AgentLoopDriver
from apps.index.models import (
    AiringBoard,
    AiringBoardEntry,
    Entity,
    EntityName,
    MatchCandidate,
    MatchEvidence,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.index.services import entity_resolution_service
from apps.sync.services.mal_service import mal_import_service

POLICY_VERSION = "mal-agent-recall-v1"
IDEMPOTENCY_SCOPE = "mal-recall:v1"
USE_CASE = "mal_recall"
TOOL_SCOPES = ("knowledge:read", "mal:read")


class RecallMalOutput(BaseModel):
    decision: Literal["found", "not_found"]
    mal_id: int | None = Field(default=None)
    confidence: float = Field(default=0, ge=0, le=1)
    reason: str = Field(min_length=1)


class MalLinkRecallService:
    POLICY_VERSION = POLICY_VERSION

    def run_missing(
        self,
        *,
        limit: int = 10,
        evaluate: bool = True,
        force: bool = False,
    ) -> dict[str, Any]:
        """Resolve active-board Bangumi works that still lack MAL candidates."""
        unresolved = self._unresolved_board_works(limit=limit)
        results = []
        for root in unresolved:
            summary = self.recall_one(
                root=root,
                evaluate=evaluate,
                force=force,
            )
            results.append(summary)
        return {
            "policy_version": POLICY_VERSION,
            "processed": len(results),
            "results": results,
        }

    def recall_one(
        self,
        *,
        root: Entity,
        evaluate: bool,
        force: bool = False,
    ) -> dict[str, Any]:
        key = self._idempotency_key(root)
        existing = (
            AgentRun.objects.filter(
                idempotency_scope=IDEMPOTENCY_SCOPE,
                idempotency_key=key,
            )
            .order_by("-created_at")
            .first()
        )
        if existing is not None:
            if existing.status == AgentRun.Status.SUCCEEDED and not force:
                return self._summary_for_run(root, existing, skipped=True)
            if existing.status in {
                AgentRun.Status.QUEUED,
                AgentRun.Status.RUNNING,
                AgentRun.Status.WAITING,
                AgentRun.Status.PAUSED,
            }:
                return self._summary_for_run(root, existing, skipped=False)
            # A failed/cancelled attempt keeps its audit trail but must free the
            # idempotency key so a fresh attempt can reuse the same scope/key.
            AgentRun.objects.filter(pk=existing.pk).update(
                idempotency_key="",
                updated_at=timezone.now(),
            )

        context = self._context(root)
        system_prompt = (
            "You identify whether an anime that currently exists in the local "
            "Bangumi-backed knowledge graph also exists on MyAnimeList.\n"
            "Rules:\n"
            "1. First search the internal knowledge graph "
            "(knowledge.search_entities / knowledge.get_entity) using each name; "
            "an imported MAL entity is a strong signal.\n"
            "2. When the internal graph is inconclusive, search the official "
            "MAL API (mal.search_anime) with original, romanized, English, and "
            "Chinese names. Prefer queries that include the season marker "
            "(II, 2nd Season, 完结季, etc.).\n"
            "3. Only report a mal_id that appeared in a tool result. Never "
            "invent an id.\n"
            "4. Verify start date/season, media type, and sequel markers before "
            "deciding. A second season of an older series must map to the "
            "correct second-season MAL id, not the first season.\n"
            "5. Return strict JSON matching the requested schema; abstain with "
            "decision=not_found when no candidate is precise enough."
        )
        run = AgentRun.objects.create(
            kind=AgentRun.Kind.ADMIN_ENRICH,
            title=f"MAL recall for Bangumi {context['bangumi_subject_id']}",
            status=AgentRun.Status.QUEUED,
            idempotency_key=key,
            idempotency_scope=IDEMPOTENCY_SCOPE,
            metadata={
                "scopes": list(TOOL_SCOPES),
                "source_root": str(root.pk),
            },
        )
        driver = AgentLoopDriver()
        try:
            run = driver.run(
                run,
                system_prompt=system_prompt,
                user_prompt=(
                    "Resolve this Bangumi work to a MAL anime id when possible.\n"
                    f"{json.dumps(context, ensure_ascii=False)}"
                ),
                tool_names=[
                    "knowledge.search_entities",
                    "knowledge.get_entity",
                    "mal.search_anime",
                ],
                output_model=RecallMalOutput,
                use_case=USE_CASE,
            )
        except Exception as exc:
            if run.status not in {
                AgentRun.Status.FAILED,
                AgentRun.Status.CANCELLED,
            }:
                run.status = AgentRun.Status.FAILED
                run.error = f"{type(exc).__name__}: {exc}"[:4000]
                run.finished_at = timezone.now()
                run.save(update_fields=["status", "error", "finished_at"])
            return {
                "root_entity_id": str(root.pk),
                "outcome": "failed",
                "error": run.error,
            }
        run.refresh_from_db()
        if run.status != AgentRun.Status.SUCCEEDED:
            return {
                "root_entity_id": str(root.pk),
                "outcome": run.status,
                "error": run.error,
            }
        final_step = run.steps.order_by("-sequence").first()
        output = (final_step.output or {}) if final_step is not None else {}
        parsed = RecallMalOutput.model_validate(output)
        if parsed.decision == "not_found":
            return {
                "root_entity_id": str(root.pk),
                "outcome": "not_found",
                "reason": parsed.reason,
            }
        candidate_id, linked_root_id = self._ensure_candidate(
            root=root,
            mal_id=parsed.mal_id,
            confidence=parsed.confidence,
            reason=parsed.reason,
        )
        result = {
            "root_entity_id": str(root.pk),
            "outcome": "candidate_created",
            "mal_id": parsed.mal_id,
            "candidate_id": candidate_id,
            "linked_root_id": linked_root_id,
            "confidence": str(parsed.confidence),
            "reason": parsed.reason,
        }
        if evaluate and candidate_id:
            self._dispatch_evaluation(candidate_id)
            result["evaluation_dispatched"] = True
        return result

    @staticmethod
    def _unresolved_board_works(*, limit: int) -> list[Entity]:
        board = AiringBoard.objects.filter(status=AiringBoard.Status.ACTIVE).first()
        if board is None:
            return []
        rows = AiringBoardEntry.objects.filter(board=board).select_related("work")
        roots: list[Entity] = []
        seen: set[Any] = set()
        for entry in rows:
            ref = (entry.source_refs or [{}])[0]
            if ref.get("provider") != "bangumi":
                continue
            root = entity_resolution_service.resolve(entry.work.entity)
            if root.pk in seen:
                continue
            if not Work.objects.filter(
                entity_id__in=entity_resolution_service.cluster_ids(root),
                work_type=Work.WorkType.ANIME,
            ).exists():
                continue
            if not MalLinkRecallService._has_pending_mal_candidate(root):
                seen.add(root.pk)
                roots.append(root)
            if len(roots) >= max(1, int(limit)):
                break
        return roots

    @staticmethod
    def _has_pending_mal_candidate(root: Entity) -> bool:
        cluster = set(entity_resolution_service.cluster_ids(root))
        candidates = MatchCandidate.objects.filter(status=MatchCandidate.Status.PENDING)
        for candidate in candidates:
            left_in = candidate.left_entity_id in cluster
            right_in = candidate.right_entity_id in cluster
            if not (left_in or right_in):
                continue
            other_id = (
                candidate.right_entity_id if left_in else candidate.left_entity_id
            )
            if MalLinkRecallService._is_mal_entity(other_id):
                return True
        return False

    @staticmethod
    def _is_mal_entity(entity_id: Any) -> bool:
        return ProviderRepresentation.objects.filter(
            entity_id=entity_id,
            is_active=True,
            provider_record__namespace__provider__slug="mal",
            provider_record__namespace__slug="anime",
        ).exists()

    @staticmethod
    def _idempotency_key(root: Entity) -> str:
        subject_id = (
            ProviderRepresentation.objects.filter(
                entity_id=root,
                is_active=True,
                provider_record__namespace__provider__slug="bangumi",
                provider_record__namespace__slug="subject",
            )
            .values_list("provider_record__external_id", flat=True)
            .first()
        )
        return f"bangumi:{subject_id or str(root.pk)}"

    @staticmethod
    def _context(root: Entity) -> dict[str, Any]:
        cluster = set(entity_resolution_service.cluster_ids(root))
        names = (
            EntityName.objects.filter(entity_id__in=cluster)
            .exclude(text="")
            .order_by("entity_id", "language", "kind")
            .values_list("text", "language", "kind")[:30]
        )
        bangumi_id = (
            ProviderRepresentation.objects.filter(
                entity_id__in=cluster,
                is_active=True,
                provider_record__namespace__provider__slug="bangumi",
                provider_record__namespace__slug="subject",
            )
            .values_list("provider_record__external_id", flat=True)
            .first()
        )
        return {
            "entity_id": str(root.pk),
            "bangumi_subject_id": bangumi_id,
            "names": [
                {"text": text, "language": language, "kind": kind}
                for text, language, kind in names
            ],
        }

    @staticmethod
    @transaction.atomic
    def _ensure_candidate(
        *,
        root: Entity,
        mal_id: int | None,
        confidence: float,
        reason: str,
    ) -> tuple[str | None, str | None]:
        if mal_id is None:
            return None, None
        mal_entity = MalLinkRecallService._resolve_mal_entity(mal_id)
        if mal_entity is None:
            try:
                mal_entity = mal_import_service.import_anime(mal_id)
            except Exception:
                return None, None
        mal_root = entity_resolution_service.resolve(mal_entity)
        if mal_root.pk == root.pk:
            return None, str(mal_root.pk)
        left, right = sorted(
            (root.pk, mal_root.pk),
            key=lambda value: str(value),
        )
        candidate, created = MatchCandidate.objects.get_or_create(
            left_entity_id=left,
            right_entity_id=right,
            policy_version=POLICY_VERSION,
            defaults={
                "score": Decimal(str(confidence)).quantize(Decimal("0.0001")),
                "runner_up_margin": Decimal("0.0000"),
                "status": MatchCandidate.Status.PENDING,
                "hard_conflicts": [],
            },
        )
        if created:
            MatchEvidence.objects.create(
                candidate=candidate,
                evidence_type="agent_mal_recall",
                value={
                    "provider_pair": "bangumi:mal",
                    "mal_id": mal_id,
                    "reason": reason,
                    "policy_version": POLICY_VERSION,
                },
                weight=Decimal(str(confidence)),
            )
        return str(candidate.pk), str(mal_root.pk)

    @staticmethod
    def _resolve_mal_entity(mal_id: int) -> Entity | None:
        record = ProviderRecord.objects.filter(
            namespace__provider__slug="mal",
            namespace__slug="anime",
            external_id=str(mal_id),
            status=ProviderRecord.Status.ACTIVE,
        ).first()
        if record is None:
            return None
        representation = ProviderRepresentation.objects.filter(
            provider_record=record,
            is_active=True,
        ).first()
        return representation.entity if representation is not None else None

    @staticmethod
    def _dispatch_evaluation(candidate_id: str) -> None:
        from config.celery import app as celery_app

        celery_app.send_task(
            "apps.ai.tasks.evaluate_match_candidate_task",
            args=[candidate_id],
            queue="ai",
        )

    @staticmethod
    def _summary_for_run(
        root: Entity, run: AgentRun, *, skipped: bool
    ) -> dict[str, Any]:
        step = run.steps.order_by("-sequence").first()
        output = (step.output or {}) if step is not None else {}
        return {
            "root_entity_id": str(root.pk),
            "outcome": "skipped_existing" if skipped else run.status,
            "run_id": str(run.pk),
            "output": output,
        }


mal_link_recall_service = MalLinkRecallService()
