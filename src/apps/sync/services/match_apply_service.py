"""Conservative admin batch for pending AI match proposals.

The normal AI policy pipeline only produces shadow proposals until a policy
has passed its evaluation gate. This service provides an explicit admin
escape hatch: it applies the same evidence-first gates in one bounded batch
and records every decision as ``decided_by=admin_batch`` so canonical merges
remain auditable. Dry-run is the default.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.ai.models import AIProposal
from apps.index.exceptions import UserLibraryConflict
from apps.index.models import MatchCandidate, MatchDecision
from apps.index.services import entity_resolution_service
from apps.users.models import UserSubject

MIN_CANDIDATE_SCORE = Decimal("0.9500")
MIN_CONFIDENCE = Decimal("0.9200")


class MatchApplyService:
    def run(
        self,
        *,
        limit: int = 200,
        apply: bool = False,
        abstain_ineligible: bool = True,
    ) -> dict[str, Any]:
        proposals = list(
            AIProposal.objects.filter(
                status=AIProposal.Status.PENDING,
                match_candidate__status=MatchCandidate.Status.PENDING,
                run__status="succeeded",
            )
            .select_related(
                "run",
                "match_candidate__left_entity",
                "match_candidate__right_entity",
            )
            .order_by("-confidence")[: max(1, int(limit))]
        )
        summary = {
            "processed": 0,
            "would_bind": 0,
            "accepted": 0,
            "abstained": 0,
            "already_bound": 0,
            "blocked": 0,
            "deferred": 0,
            "errors": [],
            "rows": [],
        }
        for proposal in proposals:
            candidate = proposal.match_candidate
            reasons = self._gate_reasons(proposal)
            eligible = not reasons
            summary["processed"] += 1
            if eligible:
                summary["would_bind"] += 1
            summary["rows"].append(
                {
                    "proposal_id": str(proposal.pk),
                    "candidate_id": str(candidate.pk),
                    "decision": proposal.payload.get("decision"),
                    "confidence": str(proposal.confidence),
                    "score": str(candidate.score),
                    "eligible": eligible,
                    "reasons": reasons,
                }
            )
            if not apply:
                continue
            if not eligible and not abstain_ineligible:
                # An unattended run must not retire a pair it merely could not
                # confirm: a weak score today may be a strong one once the
                # source names or the policy improve, and abstaining is final.
                summary["deferred"] += 1
                continue
            try:
                outcome = self._decide(
                    proposal=proposal, candidate=candidate, eligible=eligible
                )
                if outcome == "already_bound":
                    summary["already_bound"] += 1
                elif outcome == "blocked":
                    summary["blocked"] += 1
                elif eligible:
                    summary["accepted"] += 1
                else:
                    summary["abstained"] += 1
            except Exception as exc:
                summary["errors"].append(
                    {"proposal_id": str(proposal.pk), "error": str(exc)[:2000]}
                )
        return summary

    @staticmethod
    def _gate_reasons(proposal: AIProposal) -> list[str]:
        reasons: list[str] = []
        candidate = proposal.match_candidate
        decision = proposal.payload.get("decision")
        if decision != MatchDecision.Outcome.BIND:
            reasons.append(f"ai_decision={decision!r}")
        if proposal.confidence < MIN_CONFIDENCE:
            reasons.append("confidence_below_threshold")
        if candidate.score < MIN_CANDIDATE_SCORE:
            reasons.append("candidate_score_below_threshold")
        if candidate.hard_conflicts:
            reasons.append("hard_conflicts")
        if candidate.left_entity.kind != candidate.right_entity.kind:
            reasons.append("entity_kind_mismatch")
        if MatchApplyService._has_conflicting_user_library(candidate):
            reasons.append("conflicting_user_library")
        return reasons

    @staticmethod
    def _has_conflicting_user_library(candidate: MatchCandidate) -> bool:
        left_users = UserSubject.objects.filter(
            entity_id=candidate.left_entity_id
        ).values("user_id")
        return UserSubject.objects.filter(
            entity_id=candidate.right_entity_id,
            user_id__in=left_users,
        ).exists()

    @staticmethod
    @transaction.atomic
    def _decide(
        *,
        proposal: AIProposal,
        candidate: MatchCandidate,
        eligible: bool,
    ) -> str:
        candidate = MatchCandidate.objects.select_for_update().get(pk=candidate.pk)
        if candidate.status != MatchCandidate.Status.PENDING:
            proposal.status = AIProposal.Status.ABSTAINED
            proposal.policy_reason = "Candidate was already decided by another run."
            proposal.decided_at = timezone.now()
            proposal.save(update_fields=["status", "policy_reason", "decided_at"])
            return "already_decided"
        left = entity_resolution_service.resolve(candidate.left_entity)
        right = entity_resolution_service.resolve(candidate.right_entity)
        if left.pk == right.pk:
            # Another rule (the official id sweep, most often) already bound the
            # pair. Retrying would raise "already resolve together" forever and
            # leave the proposal stuck in the queue, so record the outcome and
            # move on.
            entity_resolution_service.decide_candidate(
                candidate=candidate,
                outcome=MatchDecision.Outcome.ABSTAIN,
                decided_by="admin_batch",
                reason="Already bound by another rule.",
            )
            proposal.status = AIProposal.Status.ACCEPTED
            proposal.policy_reason = "Pair already bound by another rule."
            proposal.decided_at = timezone.now()
            proposal.save(update_fields=["status", "policy_reason", "decided_at"])
            return "already_bound"
        if eligible:
            reason = (
                f"Admin conservative batch: AI bind at {proposal.confidence} "
                f"confidence on candidate score {candidate.score}."
            )
            try:
                entity_resolution_service.decide_candidate(
                    candidate=candidate,
                    outcome=MatchDecision.Outcome.BIND,
                    decided_by="admin_batch",
                    reason=reason,
                )
            except UserLibraryConflict:
                # Permanent until the user's own library entries are merged.
                # Recording it keeps the pair out of every future batch instead
                # of reporting the same error each day.
                reason = (
                    "Admin conservative batch: blocked by conflicting user "
                    "library entries."
                )
                entity_resolution_service.decide_candidate(
                    candidate=candidate,
                    outcome=MatchDecision.Outcome.ABSTAIN,
                    decided_by="admin_batch",
                    reason=reason,
                )
                proposal.status = AIProposal.Status.ABSTAINED
                proposal.policy_reason = reason
                proposal.decided_at = timezone.now()
                proposal.save(update_fields=["status", "policy_reason", "decided_at"])
                return "blocked"
            proposal.status = AIProposal.Status.ACCEPTED
            proposal.policy_reason = reason
        else:
            proposal.status = AIProposal.Status.ABSTAINED
            proposal.policy_reason = "Admin conservative batch abstained."
            entity_resolution_service.decide_candidate(
                candidate=candidate,
                outcome=MatchDecision.Outcome.ABSTAIN,
                decided_by="admin_batch",
                reason=proposal.policy_reason,
            )
        proposal.decided_at = timezone.now()
        proposal.save(update_fields=["status", "policy_reason", "decided_at"])
        return "accepted" if eligible else "abstained"


match_apply_service = MatchApplyService()
