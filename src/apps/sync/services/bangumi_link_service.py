"""MAL-anchored Bangumi linking through external search and AI selection.

Workflow per unresolved work:

1. Query the local canonical database first; if a local Bangumi candidate is
   already pending, let the normal title-similarity evaluator finish instead of
   spending external search budget.
2. Otherwise search Bangumi's subject API with the MAL names and present the
   compact result list to a reasoning model.
3. The model may only choose a subject id that appears verbatim in the search
   output. Any hallucinated/absent id is treated as abstain.
4. When a subject is selected with high confidence, the id is handed to the
   internal per-id sync (subject + episodes), then a link candidate is created
   and bound. When nothing matches, a no-match run is recorded idempotently so
   the same work is not re-searched on every daily cycle.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.ai.models import AgentRun, AgentStep, AIRun, SourceArtifact
from apps.ai.tools.evidence import capture_artifact
from apps.index.models import (
    Entity,
    EntityName,
    MatchCandidate,
    MatchDecision,
    MatchEvidence,
    ProviderRepresentation,
    Work,
)
from apps.index.services.resolution import (
    EntityResolutionError,
    entity_resolution_service,
)
from apps.sync.providers.exceptions import ProviderAPIError
from integrations.ai import AIProviderError, ai_gateway

USE_CASE = "bangumi_link_search"
POLICY_VERSION = "bangumi-search-v1"
ATTEMPT_SCOPE = "bangumi-link:v1"
PROMPT_VERSION = "bangumi-search-v1"
MIN_CONFIDENCE = Decimal("0.9200")
MAX_SEARCH_QUERIES = 2
SEARCH_LIMIT = 8


class BangumiLinkService:
    def run_missing(
        self,
        *,
        limit: int = 10,
        apply: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Resolve MAL roots that still lack a Bangumi representation."""
        limit = max(1, int(limit))
        summaries: list[dict[str, Any]] = []
        processed_roots: set[str] = set()
        mal_entity_ids = list(
            ProviderRepresentation.objects.filter(
                is_active=True,
                provider_record__namespace__provider__slug="mal",
                provider_record__namespace__slug="anime",
                provider_record__status="active",
                entity__lifecycle=Entity.Lifecycle.ACTIVE,
            )
            .values_list("entity_id", flat=True)
            .distinct()
            .order_by("entity_id")
        )
        for entity_id in mal_entity_ids:
            if len(processed_roots) >= limit:
                break
            root = entity_resolution_service.resolve(Entity.objects.get(pk=entity_id))
            if str(root.pk) in processed_roots:
                continue
            processed_roots.add(str(root.pk))
            if not self._needs_bangumi_link(root):
                continue
            try:
                summary = self.attempt(
                    root=root,
                    apply=apply,
                    force=force,
                )
            except Exception as exc:
                attempt_run = self._existing_attempt(key=self._attempt_key(root))
                if attempt_run is not None:
                    self._mark_failed(run=attempt_run, error=exc)
                summary = {
                    "root_entity_id": str(root.pk),
                    "outcome": "failed",
                    "error": f"{type(exc).__name__}: {exc}"[:2000],
                }
            summaries.append(summary)
        return {
            "policy_version": POLICY_VERSION,
            "processed": len(summaries),
            "scanned": len(processed_roots),
            "results": summaries,
        }

    @staticmethod
    def _needs_bangumi_link(root: Entity) -> bool:
        cluster_ids = entity_resolution_service.cluster_ids(root)
        if not Work.objects.filter(
            entity_id=root.pk,
            work_type=Work.WorkType.ANIME,
        ).exists():
            return False
        if ProviderRepresentation.objects.filter(
            entity_id__in=cluster_ids,
            is_active=True,
            provider_record__namespace__provider__slug="bangumi",
            provider_record__namespace__slug="subject",
            provider_record__status="active",
        ).exists():
            return False
        pending = (
            MatchCandidate.objects.filter(status=MatchCandidate.Status.PENDING)
            .exclude(policy_version=POLICY_VERSION)
            .filter(
                Q(left_entity_id__in=cluster_ids) | Q(right_entity_id__in=cluster_ids)
            )
            .exists()
        )
        return not pending

    def attempt(
        self,
        *,
        root: Entity,
        apply: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        key = self._attempt_key(root)
        existing = self._existing_attempt(key=key)
        if (
            existing is not None
            and existing.status
            in {AgentRun.Status.SUCCEEDED, AgentRun.Status.CANCELLED}
            and not force
        ):
            return {
                "root_entity_id": str(root.pk),
                "outcome": "skipped_existing",
                "attempt_id": str(existing.pk),
            }
        if existing is not None and existing.status in {
            AgentRun.Status.RUNNING,
            AgentRun.Status.WAITING,
            AgentRun.Status.PAUSED,
        }:
            return {
                "root_entity_id": str(root.pk),
                "outcome": "already_running",
                "attempt_id": str(existing.pk),
            }

        cluster_ids = entity_resolution_service.cluster_ids(root)
        names = self._names_for_cluster(cluster_ids)
        mal_ids = sorted(
            int(value)
            for value in ProviderRepresentation.objects.filter(
                entity_id__in=cluster_ids,
                is_active=True,
                provider_record__namespace__provider__slug="mal",
                provider_record__namespace__slug="anime",
                provider_record__status="active",
            ).values_list("provider_record__external_id", flat=True)
        )
        mal_id = mal_ids[0] if mal_ids else None
        run = existing
        if run is None:
            run = AgentRun.objects.create(
                kind=AgentRun.Kind.ADMIN_SYNC,
                title=f"Bangumi link for MAL {mal_id}",
                idempotency_key=key,
                idempotency_scope=ATTEMPT_SCOPE,
                metadata={
                    "source_root": str(root.pk),
                    "mal_ids": mal_ids,
                    "scopes": ["bangumi:search"],
                },
            )
            run.status = AgentRun.Status.RUNNING
            run.started_at = timezone.now()
            run.save(
                update_fields=[
                    "status",
                    "started_at",
                    "updated_at",
                ]
            )
        else:
            run.status = AgentRun.Status.RUNNING
            run.started_at = run.started_at or timezone.now()
            run.finished_at = None
            run.error = ""
            run.save(
                update_fields=[
                    "status",
                    "started_at",
                    "finished_at",
                    "error",
                    "updated_at",
                ]
            )

        queries = self._search_queries(names=names)
        candidates, artifacts, search_available = self._search_bangumi(
            queries=queries,
            agent_run=run,
        )
        if search_available is False:
            return self._mark_failed(
                run=run,
                error=RuntimeError("Bangumi search provider is unavailable."),
            )
        if not candidates:
            return self._finish(
                run=run,
                outcome="no_match",
                metadata={
                    "subject_id": None,
                    "queries": queries,
                    "candidates": 0,
                    "reason": "Bangumi search returned no anime subjects.",
                },
            )

        allowed_ids = {item["id"] for item in candidates}
        selected = self._select_subject(
            root=root,
            names=names,
            mal_id=mal_id,
            candidates=candidates,
            allowed_ids=allowed_ids,
            agent_run=run,
        )
        if selected is None:
            return self._finish(
                run=run,
                outcome="abstained",
                metadata={
                    "subject_id": None,
                    "queries": queries,
                    "candidates": len(candidates),
                    "reason": "Model abstained or confidence was below threshold.",
                },
            )

        subject_id = selected["subject_id"]
        confidence = selected["confidence"]
        artifacts.append(  # keep the decided search hit attached to the run
            capture_artifact(
                payload={
                    "root_entity_id": str(root.pk),
                    "subject_id": subject_id,
                    "confidence": str(confidence),
                    "reason": selected["reason"],
                },
                kind=SourceArtifact.Kind.INTERNAL_SNAPSHOT,
                source_url=f"https://bgm.tv/subject/{subject_id}",
                tool_name="bangumi.link",
                tool_version=PROMPT_VERSION,
                metadata={"selected": True},
            )
        )
        sync = self._sync_subject(subject_id=subject_id)
        if sync["ok"] is False:
            return self._mark_failed(
                run=run,
                error=RuntimeError(sync["error"]),
            )

        bangumi_root = entity_resolution_service.resolve(sync["entity"])
        if bangumi_root.pk == root.pk:
            return self._finish(
                run=run,
                outcome="already_linked",
                metadata={
                    "subject_id": subject_id,
                    "canonical_entity_id": str(root.pk),
                },
            )

        candidate = self._create_candidate(
            root=root,
            bangumi_root=bangumi_root,
            subject_id=subject_id,
            confidence=confidence,
            names=names,
        )
        if candidate is None:
            return self._finish(
                run=run,
                outcome="abstained",
                metadata={
                    "subject_id": subject_id,
                    "reason": "Canonical pair is not a compatible anime Work.",
                },
            )

        if not apply:
            self._finish(
                run=run,
                outcome="candidate_pending",
                metadata={
                    "subject_id": subject_id,
                    "candidate_id": str(candidate.pk),
                    "confidence": str(confidence),
                    "episodes_synced": sync["episodes_synced"],
                    "reason": selected["reason"],
                },
            )
            return {
                "root_entity_id": str(root.pk),
                "outcome": "candidate_pending",
                "subject_id": subject_id,
                "candidate_id": str(candidate.pk),
            }

        try:
            entity_resolution_service.decide_candidate(
                candidate=candidate,
                outcome=MatchDecision.Outcome.BIND,
                decided_by="ai_bangumi_search",
                reason=(
                    f"AI Bangumi search matched subject {subject_id} at "
                    f"{confidence} confidence; evidence includes MAL title and "
                    "Bangumi search result."
                ),
            )
        except EntityResolutionError as exc:
            entity_resolution_service.decide_candidate(
                candidate=candidate,
                outcome=MatchDecision.Outcome.ABSTAIN,
                decided_by="ai_bangumi_search",
                reason=f"Bangumi link could not be bound safely: {exc}",
            )
            return self._finish(
                run=run,
                outcome="abstained",
                metadata={
                    "subject_id": subject_id,
                    "candidate_id": str(candidate.pk),
                    "error": str(exc),
                },
            )

        return self._finish(
            run=run,
            outcome="linked",
            metadata={
                "subject_id": subject_id,
                "candidate_id": str(candidate.pk),
                "confidence": str(confidence),
                "episodes_synced": sync["episodes_synced"],
                "reason": selected["reason"],
            },
        )

    @staticmethod
    def _attempt_key(root: Entity) -> str:
        cluster_ids = entity_resolution_service.cluster_ids(root)
        mal_ids = sorted(
            int(value)
            for value in ProviderRepresentation.objects.filter(
                entity_id__in=cluster_ids,
                is_active=True,
                provider_record__namespace__provider__slug="mal",
                provider_record__namespace__slug="anime",
                provider_record__status="active",
            ).values_list("provider_record__external_id", flat=True)
        )
        anchor = mal_ids[0] if mal_ids else str(root.pk).replace("-", "")
        return f"mal:{anchor}"

    @staticmethod
    def _existing_attempt(*, key: str) -> AgentRun | None:
        return (
            AgentRun.objects.filter(
                idempotency_scope=ATTEMPT_SCOPE,
                idempotency_key=key,
            )
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def _names_for_cluster(cluster_ids: set[Any]) -> list[str]:
        rows = (
            EntityName.objects.filter(entity_id__in=cluster_ids)
            .exclude(text="")
            .order_by("id")
            .values_list("text", flat=True)
        )
        seen: set[str] = set()
        names: list[str] = []
        for text in rows:
            normalized = " ".join(str(text).strip().split())
            key = normalized.casefold()
            if not normalized or key in seen:
                continue
            seen.add(key)
            names.append(normalized[:512])
            if len(names) >= 16:
                break
        return names

    @staticmethod
    def _search_queries(*, names: list[str]) -> list[str]:
        """Choose search keywords without calling the model twice."""
        queries: list[str] = []
        for name in names:
            if name not in queries:
                queries.append(name)
            if len(queries) >= MAX_SEARCH_QUERIES:
                break
        return queries

    def _search_bangumi(
        self,
        *,
        queries: list[str],
        agent_run: AgentRun,
    ) -> tuple[list[dict[str, Any]], list[SourceArtifact], bool]:
        """Search Bangumi and keep a compact deduplicated candidate list."""
        from apps.ai.tools.bangumi import (
            BangumiSearchInput,
            BangumiSearchTool,
        )

        candidates: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        artifacts: list[SourceArtifact] = []
        available = True
        tool = BangumiSearchTool()
        for query in queries:
            result = tool.execute(BangumiSearchInput(keyword=query, limit=SEARCH_LIMIT))
            if result.available is False:
                available = False
                break
            for item in result.results:
                subject_id = int(item["id"])
                if subject_id in seen_ids:
                    continue
                seen_ids.add(subject_id)
                item["matched_query"] = query
                candidates.append(item)
                artifacts.append(
                    capture_artifact(
                        payload=item,
                        kind=SourceArtifact.Kind.SEARCH_RESULT,
                        source_url=str(item["url"]),
                        tool_name="bangumi.search_subjects",
                        tool_version="1.0.0",
                        metadata={"query": query},
                    )
                )
        return candidates[: min(SEARCH_LIMIT * 2, 16)], artifacts, available

    @staticmethod
    def _select_subject(
        *,
        root: Entity,
        names: list[str],
        mal_id: int | None,
        candidates: list[dict[str, Any]],
        allowed_ids: set[int],
        agent_run: AgentRun,
    ) -> dict[str, Any] | None:
        step = AgentStep.objects.create(
            run=agent_run,
            sequence=agent_run.steps.count(),
            kind=AgentStep.Kind.MODEL,
            skill_name="",
            skill_version="",
            input_hash="",
            input={"use_case": USE_CASE},
            status=AgentStep.Status.RUNNING,
            started_at=timezone.now(),
        )
        payload = {
            "source": {
                "kind": "anime",
                "mal_id": mal_id,
                "names": names,
                "entity_id": str(root.pk),
            },
            "candidates": candidates,
            "rule": (
                "Select the single Bangumi subject that is the same anime as "
                "the source work. Never invent a subject_id that is not in the "
                "candidate list. Only choose found when the match is highly "
                "confident (title and broadcast date/season agree); otherwise "
                "return not_found."
            ),
        }
        ai_run = AIRun.objects.create(
            agent_step=step,
            use_case=USE_CASE,
            provider=ai_gateway.provider_name,
            model=ai_gateway.resolve_model(USE_CASE),
            prompt_version=PROMPT_VERSION,
            input_hash=_payload_hash(payload),
            input_metadata={"root_entity_id": str(root.pk)},
            status=AIRun.Status.RUNNING,
            started_at=timezone.now(),
        )
        started = timezone.now()
        system_prompt = (
            "You resolve anime identity between a MAL-anchored work and "
            "Bangumi search results. Return strict JSON with fields "
            "{decision: found|not_found, subject_id: int|null, "
            "confidence: 0..1, reason: string}. subject_id must be one of the "
            "ids present in candidates. Never guess an id outside the list. "
            "Prefer abstaining (not_found) when the broadcast season, studio "
            "timing, or title evidence is ambiguous."
        )
        try:
            raw, usage = ai_gateway.complete_json(
                system_prompt=system_prompt,
                payload=payload,
                use_case=USE_CASE,
            )
        except AIProviderError as exc:
            ai_run.status = AIRun.Status.FAILED
            ai_run.error = f"{type(exc).__name__}: {exc}"[:4000]
            ai_run.finished_at = timezone.now()
            ai_run.save(update_fields=["status", "error", "finished_at"])
            step.status = AgentStep.Status.FAILED
            step.error = ai_run.error
            step.finished_at = timezone.now()
            step.save(update_fields=["status", "error", "finished_at"])
            raise
        decision = _validate_output(raw, allowed_ids=allowed_ids)
        stored_decision = {
            "decision": decision["decision"],
            "subject_id": decision.get("subject_id"),
            "confidence": str(decision["confidence"]),
            "reason": decision["reason"],
        }
        ai_run.status = AIRun.Status.SUCCEEDED
        ai_run.output = stored_decision
        ai_run.input_tokens = _optional_int(usage.get("input_tokens"))
        ai_run.output_tokens = _optional_int(usage.get("output_tokens"))
        ai_run.latency_ms = max(
            0, int((timezone.now() - started).total_seconds() * 1000)
        )
        ai_run.finished_at = timezone.now()
        ai_run.save(
            update_fields=[
                "status",
                "output",
                "input_tokens",
                "output_tokens",
                "latency_ms",
                "finished_at",
            ]
        )
        step.output = stored_decision
        step.status = AgentStep.Status.SUCCEEDED
        step.finished_at = timezone.now()
        step.save(update_fields=["output", "status", "finished_at"])
        if (
            decision["decision"] != "found"
            or decision.get("subject_id") not in allowed_ids
            or decision["confidence"] < MIN_CONFIDENCE
        ):
            return None
        return decision

    @staticmethod
    def _sync_subject(*, subject_id: int) -> dict[str, Any]:
        from apps.sync.services.episode_service import episode_service
        from apps.sync.services.subject_service import subject_service

        try:
            entity = subject_service.upsert_subject(int(subject_id))
        except ProviderAPIError as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:2000]}
        episodes_synced = False
        try:
            episode_service.sync_subject_episodes(int(subject_id))
            episodes_synced = True
        except Exception as exc:
            return {
                "ok": True,
                "entity": entity,
                "episodes_synced": episodes_synced,
                "episode_error": f"{type(exc).__name__}: {exc}"[:2000],
            }
        return {"ok": True, "entity": entity, "episodes_synced": True}

    @staticmethod
    def _create_candidate(
        *,
        root: Entity,
        bangumi_root: Entity,
        subject_id: int,
        confidence: Decimal,
        names: list[str],
    ) -> MatchCandidate | None:
        left_types = set(
            Work.objects.filter(entity_id__in=(root.pk, bangumi_root.pk)).values_list(
                "work_type", flat=True
            )
        )
        if not left_types <= {Work.WorkType.ANIME}:
            return None
        left, right = sorted((root, bangumi_root), key=lambda item: str(item.pk))
        candidate, created = MatchCandidate.objects.get_or_create(
            left_entity=left,
            right_entity=right,
            policy_version=POLICY_VERSION,
            defaults={
                "score": confidence,
                "runner_up_margin": Decimal("0.1000"),
                "status": MatchCandidate.Status.PENDING,
                "hard_conflicts": [],
            },
        )
        if not created:
            return (
                candidate if candidate.status == MatchCandidate.Status.PENDING else None
            )
        MatchEvidence.objects.create(
            candidate=candidate,
            evidence_type="provider_search",
            value={
                "provider": "bangumi",
                "subject_id": subject_id,
                "source_url": f"https://bgm.tv/subject/{subject_id}",
                "matched_names": names[:8],
                "policy_version": POLICY_VERSION,
            },
            weight=confidence,
        )
        return candidate

    @staticmethod
    def _mark_failed(*, run: AgentRun, error: Exception) -> dict[str, Any]:
        merged = dict(run.metadata or {})
        merged["outcome"] = "failed"
        merged["error"] = f"{type(error).__name__}: {error}"[:4000]
        run.metadata = merged
        run.status = AgentRun.Status.FAILED
        run.error = merged["error"]
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                "metadata",
                "status",
                "error",
                "finished_at",
                "updated_at",
            ]
        )
        return {
            "root_entity_id": merged.get("source_root") or "",
            "outcome": "failed",
            "attempt_id": str(run.pk),
            "error": merged["error"],
        }

    @staticmethod
    def _finish(
        *,
        run: AgentRun,
        outcome: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(run.metadata or {})
        merged.update(metadata)
        merged["outcome"] = outcome
        run.metadata = merged
        run.status = AgentRun.Status.SUCCEEDED
        run.finished_at = timezone.now()
        run.save(update_fields=["metadata", "status", "finished_at", "updated_at"])
        return {
            "root_entity_id": metadata.get("source_root")
            or merged.get("source_root")
            or "",
            "outcome": outcome,
            "attempt_id": str(run.pk),
            **{key: value for key, value in metadata.items() if key != "source_root"},
        }


def _validate_output(raw: dict[str, Any], *, allowed_ids: set[int]) -> dict[str, Any]:
    decision = raw.get("decision")
    if decision not in {"found", "not_found"}:
        raise ValueError("Bangumi link model decision must be found or not_found.")
    raw_subject_id = raw.get("subject_id")
    subject_id = (
        int(raw_subject_id)
        if raw_subject_id is not None and not isinstance(raw_subject_id, bool)
        else None
    )
    try:
        confidence = Decimal(str(raw.get("confidence")))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Bangumi link confidence must be a number.") from exc
    if not confidence.is_finite() or not 0 <= confidence <= 1:
        raise ValueError("Bangumi link confidence must be between 0 and 1.")
    if decision == "found" and (subject_id is None or subject_id not in allowed_ids):
        # A hallucinated id must never become a link target.
        decision = "not_found"
        subject_id = None
        confidence = Decimal("0")
    if decision == "not_found":
        subject_id = None
    reason = str(raw.get("reason") or "").strip()[:2000]
    return {
        "decision": decision,
        "subject_id": subject_id,
        "confidence": confidence,
        "reason": reason,
    }


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _payload_hash(payload: dict[str, Any]) -> str:
    import hashlib

    encoded = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


bangumi_link_service = BangumiLinkService()
