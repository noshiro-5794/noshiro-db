"""Bounded AI/web completion for tentative board schedule slots.

The service only touches the curated ``AiringBoardEntry`` projection, never the
provider-owned ``AiringEvent`` facts. Every proposed slot is persisted as an
``AIClaim`` bound to a web ``SourceArtifact``; the board is updated only when a
calibrated confidence threshold is met.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

from apps.ai.models import (
    AgentRun,
    AgentStep,
    AIClaim,
    ClaimEvidence,
    SourceArtifact,
)
from apps.ai.tools.evidence import capture_artifact
from apps.ai.tools.web import WebSearchInput, web_search_tool
from apps.index.models import (
    AiringBoard,
    AiringBoardEntry,
    EntityName,
)
from integrations.ai import ai_gateway

USE_CASE = "schedule_completion"
PROMPT_VERSION = "schedule-completion-v1"

SYSTEM_PROMPT = (
    "You complete one anime weekly broadcast slot for a board projection. "
    "Use only the supplied web search results as evidence; never invent a "
    "broadcast time. Return JSON exactly matching: "
    '{"decision":"accept"|"abstain","weekday":1..7 or null,'
    '"time":"HH:MM" or null,"timezone":"Asia/Tokyo" or "",'
    '"duration_minutes":integer or null,"confidence":0..1,"reason":"..."}. '
    "Abstain when results contain no explicit broadcast day and time."
)


class ScheduleCompletionService:
    USE_CASE = USE_CASE
    PROMPT_VERSION = PROMPT_VERSION

    def pending_entries(
        self,
        *,
        limit: int | None = None,
    ) -> list[AiringBoardEntry]:
        board = AiringBoard.objects.filter(status=AiringBoard.Status.ACTIVE).first()
        if board is None:
            return []
        entries = (
            AiringBoardEntry.objects.filter(
                board=board,
                starts_at__isnull=True,
                precision__in=(
                    AiringBoardEntry.Precision.DAY,
                    AiringBoardEntry.Precision.WEEKDAY,
                    AiringBoardEntry.Precision.UNKNOWN,
                ),
            )
            .select_related("work__entity")
            .order_by("created_at")
        )
        if limit:
            entries = entries[: max(1, int(limit))]
        return list(entries)

    def run(
        self,
        *,
        limit: int | None = None,
        apply: bool = True,
    ) -> dict[str, Any]:
        entries = self.pending_entries(limit=limit)
        summary = {
            "pending": len(entries),
            "searched": 0,
            "accepted": 0,
            "abstained": 0,
            "skipped_no_search": 0,
            "claims": [],
            "applied": 0,
        }
        if settings.WEB_SEARCH_PROVIDER != "tavily" or not settings.WEB_SEARCH_API_KEY:
            summary["skipped_no_search"] = len(entries)
            return summary
        run = AgentRun.objects.create(
            kind=AgentRun.Kind.ADMIN_ENRICH,
            title="Airing board schedule completion",
            idempotency_scope="board:schedule-completion",
            idempotency_key="",
            status=AgentRun.Status.RUNNING,
        )
        try:
            for index, entry in enumerate(entries):
                result = self._complete_entry(
                    entry=entry,
                    run=run,
                    sequence=index,
                    apply=apply,
                )
                summary[result["bucket"]] += 1
                if result.get("claim_id"):
                    summary["claims"].append(str(result["claim_id"]))
                if result.get("applied"):
                    summary["applied"] += 1
            run.status = AgentRun.Status.SUCCEEDED
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "finished_at", "updated_at"])
        except Exception:
            run.status = AgentRun.Status.FAILED
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "finished_at", "updated_at"])
            raise
        return summary

    @staticmethod
    def _complete_entry(
        *,
        entry: AiringBoardEntry,
        run: AgentRun,
        sequence: int,
        apply: bool,
    ) -> dict[str, Any]:
        work = entry.work
        entity = work.entity
        title = (
            EntityName.objects.filter(entity=entity, kind=EntityName.Kind.ORIGINAL)
            .values_list("text", flat=True)
            .first()
        ) or str(work.entity_id)
        query = f"{title} 放送 曜日 時刻 アニメ"
        search = web_search_tool.execute(WebSearchInput(query=query, max_results=5))
        if not search.available or not search.results:
            return {"bucket": "abstained"}
        artifact = capture_artifact(
            payload={"results": search.results},
            kind=SourceArtifact.Kind.SEARCH_RESULT,
            source_url=str(search.results[0].get("url") or ""),
            tool_name="web.search",
            tool_version="1.0.0",
            metadata={"query": query},
        )
        payload = {
            "work_id": str(entity.id),
            "title": title,
            "season_key": entry.board.season_key,
            "source_refs": entry.source_refs,
            "search_results": search.results,
        }
        output, _usage = ai_gateway.complete_json(
            use_case=USE_CASE,
            system_prompt=SYSTEM_PROMPT,
            payload=payload,
        )
        parsed = validate_slot_output(output)
        step = AgentStep.objects.create(
            run=run,
            sequence=sequence,
            kind=AgentStep.Kind.SKILL,
            skill_name="schedule_completion",
            skill_version="1.0.0",
            input_hash=hashlib.sha256(
                json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
            input=payload,
            output=parsed,
            status=AgentStep.Status.SUCCEEDED,
            finished_at=timezone.now(),
        )
        if parsed["decision"] != "accept":
            step.status = AgentStep.Status.SUCCEEDED
            step.output = parsed
            step.save(update_fields=["status", "output"])
            return {"bucket": "abstained"}
        confidence = Decimal(str(parsed["confidence"]))
        claim = AIClaim.objects.create(
            step=step,
            target_entity=entity,
            claim_type=USE_CASE,
            predicate_slug="broadcast-slot",
            proposed_value=parsed,
            model_confidence=confidence,
            evidence_strength=Decimal("1.0000"),
            status=AIClaim.Status.PROPOSED,
        )
        ClaimEvidence.objects.create(
            claim=claim,
            artifact=artifact,
            locator="web.search",
            excerpt=artifact.excerpt,
            excerpt_hash=artifact.content_hash,
        )
        applied = False
        if apply and confidence >= Decimal(str(settings.AI_ENRICH_MIN_CONFIDENCE)):
            _apply_slot_to_board(entry=entry, parsed=parsed, claim=claim)
            claim.status = AIClaim.Status.ACCEPTED
            claim.policy_decision = "auto_apply"
            claim.policy_reason = "Confidence cleared the board completion threshold."
            claim.decided_at = timezone.now()
            claim.save(
                update_fields=[
                    "status",
                    "policy_decision",
                    "policy_reason",
                    "decided_at",
                ]
            )
            applied = True
        return {
            "bucket": "accepted",
            "claim_id": claim.id,
            "applied": applied,
        }


schedule_completion_service = ScheduleCompletionService()


def validate_slot_output(output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        raise ValueError("Schedule completion output must be an object.")
    decision = str(output.get("decision") or "")
    if decision not in {"accept", "abstain"}:
        raise ValueError("Schedule completion decision must be accept or abstain.")
    confidence = float(output.get("confidence") or 0)
    if not 0 <= confidence <= 1:
        raise ValueError("Schedule completion confidence must be between 0 and 1.")
    weekday = output.get("weekday")
    if decision == "accept":
        if not isinstance(weekday, int) or not 1 <= weekday <= 7:
            raise ValueError("Accepted slot requires weekday 1..7.")
        if not isinstance(output.get("time"), str) or ":" not in output["time"]:
            raise ValueError("Accepted slot requires HH:MM time.")
    return {
        "decision": decision,
        "weekday": weekday,
        "time": output.get("time"),
        "timezone": str(output.get("timezone") or "Asia/Tokyo"),
        "duration_minutes": output.get("duration_minutes"),
        "confidence": confidence,
        "reason": str(output.get("reason") or ""),
    }


def _apply_slot_to_board(
    *,
    entry: AiringBoardEntry,
    parsed: dict[str, Any],
    claim: AIClaim,
) -> None:
    zone = _zone(parsed["timezone"])
    hour, minute = parsed["time"].split(":", 1)
    slot = _next_slot(
        weekday=int(parsed["weekday"]),
        hour=int(hour),
        minute=int(minute[:2]),
        zone=zone,
    )
    refs = list(entry.source_refs or [])
    refs.append(
        {
            "provider": "web",
            "namespace": "schedule-completion",
            "external_id": "",
            "claim_id": str(claim.id),
            "method": "web_evidence",
        }
    )
    entry.weekday = parsed["weekday"]
    entry.starts_at = slot
    entry.timezone = parsed["timezone"]
    if isinstance(parsed["duration_minutes"], int) and parsed["duration_minutes"] > 0:
        entry.duration_minutes = parsed["duration_minutes"]
    entry.precision = AiringBoardEntry.Precision.MINUTE
    entry.status = AiringBoardEntry.Status.SCHEDULED
    entry.decision = AiringBoardEntry.Decision.AI
    entry.confidence = Decimal(str(parsed["confidence"]))
    entry.source_refs = refs
    entry.save(
        update_fields=[
            "weekday",
            "starts_at",
            "timezone",
            "duration_minutes",
            "precision",
            "status",
            "decision",
            "confidence",
            "source_refs",
            "updated_at",
        ]
    )


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Asia/Tokyo")


def _next_slot(
    *,
    weekday: int,
    hour: int,
    minute: int,
    zone: ZoneInfo,
) -> datetime:
    local_now = timezone.now().astimezone(zone)
    days_ahead = (weekday - local_now.isoweekday()) % 7
    slot = datetime.combine(
        local_now.date() + timedelta(days=days_ahead),
        time(hour=hour, minute=minute),
        tzinfo=zone,
    )
    if slot <= local_now:
        slot += timedelta(days=7)
    return slot.astimezone(UTC)
