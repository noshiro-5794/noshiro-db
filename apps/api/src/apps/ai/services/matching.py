from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from apps.ai.models import AIEvaluationRun, AIPolicy, AIProposal, AIRun
from apps.index.models import CandidateDecision, MatchCandidate, Work
from apps.index.services import entity_resolution_service, work_families
from apps.users.models import UserLibraryEntry
from integrations.ai import ai_gateway

from .common import (
    ENTITY_MATCHING_USE_CASE,
    ai_input_hash,
    optional_non_negative_decimal,
    optional_non_negative_int,
    validate_matching_output,
)


class AIMatchingService:
    USE_CASE = ENTITY_MATCHING_USE_CASE
    # v2 adds the structured picture of both works (names, release date, episode
    # count, platform, links) to the payload; v1 showed the model two title
    # strings and a score, which is why a third of its verdicts were abstentions.
    PROMPT_VERSION = "entity-match-v2"
    SYSTEM_PROMPT = (
        "Decide whether two knowledge-base works from different providers are "
        "the same real work. The payload gives you left_work and right_work - "
        "each with the names the provider stores, the release date, the episode "
        "count, the platform and the external links the catalogue already holds "
        "- and comparison, which summarises how far the two sides agree. A hard "
        "conflict means the two cannot be the same work. Bind only when the "
        "titles agree AND at least one independent attribute corroborates them "
        "(release date within a year, matching episode count, or matching "
        "platform); a translated or romanised title alone is not enough, because "
        "unrelated works share translations. Return strict JSON with decision "
        "(bind, group, reject, or abstain), confidence from 0 to 1, and a concise "
        "reason. Use 'group' when the works belong to the same season or series "
        "at different granularity (e.g. one whole season versus its split cours) "
        "and must not be merged. Abstain whenever the evidence leaves real doubt."
    )

    def evaluate(self, *, candidate_id) -> AIProposal:
        candidate = MatchCandidate.objects.select_related(
            "left_entity", "right_entity"
        ).get(pk=candidate_id)
        policy, _ = AIPolicy.objects.get_or_create(
            use_case=self.USE_CASE,
            defaults={"policy_version": candidate.policy_version},
        )
        evidence = [
            {
                "evidence_type": item["evidence_type"],
                "value": item["value"],
                "weight": str(item["weight"]),
            }
            for item in candidate.evidence.order_by("evidence_type").values(
                "evidence_type", "value", "weight"
            )
        ]
        sides = self._structured_sides(candidate=candidate, evidence=evidence)
        payload = {
            "left_entity_id": str(candidate.left_entity_id),
            "right_entity_id": str(candidate.right_entity_id),
            "resolver_score": str(candidate.score),
            "runner_up_margin": str(candidate.runner_up_margin),
            "hard_conflicts": candidate.hard_conflicts,
            "left_work": sides.get("left"),
            "right_work": sides.get("right"),
            "comparison": sides.get("comparison"),
            "evidence": evidence,
        }
        run = AIRun.objects.create(
            use_case=self.USE_CASE,
            provider=ai_gateway.provider_name,
            model=ai_gateway.resolve_model(self.USE_CASE),
            prompt_version=self.PROMPT_VERSION,
            input_hash=ai_input_hash(payload),
            input_metadata={"candidate_id": str(candidate.id)},
            status=AIRun.Status.RUNNING,
            started_at=timezone.now(),
        )
        started = timezone.now()
        try:
            raw_output, usage = ai_gateway.complete_json(
                use_case=self.USE_CASE,
                system_prompt=self.SYSTEM_PROMPT,
                payload=payload,
            )
            output = validate_matching_output(raw_output)
        except Exception as exc:
            self._mark_run_failed(run=run, error=exc)
            raise

        latency_ms = int((timezone.now() - started).total_seconds() * 1000)
        return self._persist_result(
            run=run,
            candidate_id=candidate.id,
            policy_id=policy.id,
            output=output,
            usage=usage,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _mark_run_failed(*, run: AIRun, error: Exception) -> None:
        run.status = AIRun.Status.FAILED
        run.error = f"{type(error).__name__}: {error}"[:4000]
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "error", "finished_at"])

    @transaction.atomic
    def _persist_result(
        self,
        *,
        run: AIRun,
        candidate_id,
        policy_id: int,
        output: dict[str, Any],
        usage: dict[str, Any],
        latency_ms: int,
    ) -> AIProposal:
        candidate = MatchCandidate.objects.select_for_update().get(pk=candidate_id)
        policy = AIPolicy.objects.get(pk=policy_id)
        run.status = AIRun.Status.SUCCEEDED
        run.output = output
        run.input_tokens = optional_non_negative_int(usage.get("input_tokens"))
        run.output_tokens = optional_non_negative_int(usage.get("output_tokens"))
        run.cost = optional_non_negative_decimal(usage.get("cost"))
        run.latency_ms = max(0, latency_ms)
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "output",
                "input_tokens",
                "output_tokens",
                "cost",
                "latency_ms",
                "finished_at",
            ]
        )
        proposal = AIProposal.objects.create(
            run=run,
            match_candidate=candidate,
            proposal_type=self.USE_CASE,
            payload=output,
            confidence=Decimal(output["confidence"]),
        )
        self._apply_policy(proposal=proposal, candidate=candidate, policy=policy)
        return proposal

    @staticmethod
    def _structured_sides(
        *, candidate: MatchCandidate, evidence: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Map the generator's ``work_attributes`` evidence onto left and right.

        The evidence names its sides source and target; the candidate stores them
        as left and right in id order, so the ids the generator recorded are what
        puts each provider's attributes in front of the model under the side it
        can actually see.
        """
        row = next(
            (item for item in evidence if item["evidence_type"] == "work_attributes"),
            None,
        )
        if row is None or not isinstance(row.get("value"), dict):
            return {}
        value = row["value"]
        source = value.get("source")
        target = value.get("target")
        source_id = value.get("source_entity_id")
        target_id = value.get("target_entity_id")
        sides: dict[str, Any] = {"comparison": value.get("comparison")}
        if source_id and str(source_id) == str(candidate.left_entity_id):
            sides["left"], sides["right"] = source, target
        elif target_id and str(target_id) == str(candidate.left_entity_id):
            sides["left"], sides["right"] = target, source
        else:
            # Evidence written before the ids were recorded: still surface both
            # sides, just without claiming which is which.
            sides["left"], sides["right"] = source, target
        return sides

    @staticmethod
    def _work_types(candidate: MatchCandidate) -> dict[str, set[str]]:
        """Work types of each side's resolved cluster, for the family gate.

        A pair whose types cannot be read comes back empty, which the family gate
        refuses: an automatic bind must fail closed rather than merge something it
        could not classify.
        """
        types: dict[str, set[str]] = {}
        try:
            for side in ("left_entity", "right_entity"):
                entity = getattr(candidate, side)
                cluster = entity_resolution_service.cluster_ids(entity)
                types[side] = set(
                    Work.objects.filter(entity_id__in=cluster).values_list(
                        "work_type", flat=True
                    )
                )
        except (AttributeError, TypeError, ValueError, ObjectDoesNotExist):
            return {"left_entity": set(), "right_entity": set()}
        return types

    @staticmethod
    def _policy_is_production_ready(
        *, policy: AIPolicy, candidate: MatchCandidate
    ) -> bool:
        if (
            not policy.is_enabled
            or policy.shadow_mode
            or policy.policy_version != candidate.policy_version
        ):
            return False
        evaluation = (
            AIEvaluationRun.objects.filter(
                use_case=policy.use_case,
                policy_version=policy.policy_version,
                passed=True,
            )
            .order_by("-created_at")
            .first()
        )
        return bool(
            evaluation
            and evaluation.sample_count > 0
            and evaluation.precision >= policy.required_evaluation_precision
        )

    @staticmethod
    def _has_conflicting_user_library_data(candidate: MatchCandidate) -> bool:
        left_users = UserLibraryEntry.objects.filter(
            entity_id=candidate.left_entity_id
        ).values("user_id")
        return UserLibraryEntry.objects.filter(
            entity_id=candidate.right_entity_id,
            user_id__in=left_users,
        ).exists()

    def _apply_policy(
        self,
        *,
        proposal: AIProposal,
        candidate: MatchCandidate,
        policy: AIPolicy,
    ) -> None:
        if candidate.status != MatchCandidate.Status.PENDING:
            self._finish_proposal(
                proposal,
                status=AIProposal.Status.ABSTAINED,
                reason="Candidate was already decided by another run.",
            )
            return
        if not self._policy_is_production_ready(policy=policy, candidate=candidate):
            proposal.policy_reason = (
                "Shadow proposal only; policy is disabled, version-mismatched, "
                "or has not passed its production evaluation gate."
            )
            proposal.save(update_fields=["policy_reason"])
            return

        evidence_types = candidate.evidence.values("evidence_type").distinct().count()
        # Only works in the same family may be merged: an anime with an anime, a
        # galgame with a galgame or the broader game type. A pair whose types are
        # unknown is refused rather than merged, because an automatic gate cannot
        # see the difference between "same work" and "same kind of record".
        work_types = self._work_types(candidate)
        bind_allowed = all(
            (
                proposal.payload["decision"] == CandidateDecision.Outcome.BIND,
                proposal.confidence >= policy.minimum_score,
                candidate.score >= policy.minimum_score,
                candidate.runner_up_margin >= policy.minimum_margin,
                evidence_types >= policy.minimum_evidence_types,
                candidate.left_entity.kind == candidate.right_entity.kind,
                work_families.are_bindable(
                    work_types["left_entity"], work_types["right_entity"]
                ),
                not candidate.hard_conflicts,
                not self._has_conflicting_user_library_data(candidate),
            )
        )
        if bind_allowed:
            reason = "Passed calibrated conservative auto-bind gate."
            self._finish_proposal(
                proposal,
                status=AIProposal.Status.ACCEPTED,
                reason=reason,
            )
            entity_resolution_service.decide_candidate(
                candidate=candidate,
                outcome=CandidateDecision.Outcome.BIND,
                decided_by="ai_policy",
                reason=reason,
            )
            return

        reason = "Conservative policy abstained because one or more bind gates failed."
        self._finish_proposal(
            proposal,
            status=AIProposal.Status.ABSTAINED,
            reason=reason,
        )
        entity_resolution_service.decide_candidate(
            candidate=candidate,
            outcome=CandidateDecision.Outcome.ABSTAIN,
            decided_by="ai_policy",
            reason=reason,
        )

    @staticmethod
    def _finish_proposal(proposal: AIProposal, *, status: str, reason: str) -> None:
        proposal.status = status
        proposal.policy_reason = reason
        proposal.decided_at = timezone.now()
        proposal.save(update_fields=["status", "policy_reason", "decided_at"])


ai_matching_service = AIMatchingService()
