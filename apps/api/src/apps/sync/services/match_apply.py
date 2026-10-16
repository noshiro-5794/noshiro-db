"""Conservative admin batch for pending AI match proposals.

The normal AI policy pipeline only produces shadow proposals until a policy
has passed its evaluation gate. This service provides an explicit admin
escape hatch: it applies the same evidence-first gates in one bounded batch
and records every decision as ``decided_by=admin_batch`` so canonical merges
remain auditable. Dry-run is the default.

Two properties matter:

* **Rotation.** The batch walks the pending set in creation order and records
  how far it got in ``SyncState``, so a proposal that stays pending is not
  examined again until the rest of the set has been seen. The previous version
  took the highest-confidence ``limit`` rows on every run and, when a gate
  refused a proposal, simply left it pending (the scheduled
  ``apply_match_proposals_task`` passes ``abstain_ineligible=False``, so an
  unattended pass may not retire a pair it could not confirm). Every run was
  therefore handed the same confident, ineligible head and never reached the
  eligible proposals ranked below the batch size: 2,666 proposals sat pending
  since 2026-10-07 while the daily task ran.
* **A stable ordinal.** The cursor is a position in creation order rather than
  in ``-confidence`` order, because creation order is append-only: a proposal
  evaluated while a pass is running joins the set at the end, behind the
  cursor. A new high-confidence row would join in front of the cursor instead,
  displacing the rows it has not reached yet, which is the shape the bug had.
  Confidence is consequently no longer what decides which rows a run sees.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from apps.ai.models import AIProposal
from apps.index.exceptions import UserLibraryConflict
from apps.index.models import MatchCandidate, MatchDecision, Work
from apps.index.services import entity_resolution_service, work_families
from apps.sync.models import SyncState
from apps.users.models import UserSubject

# There is one ring of pending proposals, so the SyncState row identifies the
# batch itself rather than a provider pair the way a sweep shard does.
ROTATION_TASK_NAME = "match_apply_rotation"
ROTATION_SHARD = "pending"

MIN_CANDIDATE_SCORE = Decimal("0.9500")
MIN_CONFIDENCE = Decimal("0.9200")
# Sources disagree about a premiere by a year often enough that one year of
# slack is expected; two or more decades-coded remakes apart is not.
RELEASE_YEAR_TOLERANCE = 1


class MatchApplyService:
    def run(
        self,
        *,
        limit: int = 200,
        apply: bool = False,
        abstain_ineligible: bool = True,
    ) -> dict[str, Any]:
        """Apply the next window of the pending proposal ring.

        ``limit`` bounds the window, not the whole pending set: the cursor in
        ``SyncState`` makes the next run continue where this one stopped, so a
        proposal that stays pending is not examined again until a full pass has
        gone by. ``abstain_ineligible`` keeps its meaning - an admin run may
        retire a pair the gates refused, the scheduled run may only defer it -
        and the rotation is what stops those deferrals from pinning every run
        to the same rows.
        """
        proposals, cursor, pending, completed_pass = self._sweep_window(
            batch=max(1, int(limit))
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
            "cursor_before": cursor,
            "cursor_after": cursor,
            "pending": pending,
            "completed_pass": completed_pass,
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
        if apply and proposals:
            self._advance_cursor(
                proposals=proposals,
                cursor=cursor,
                pending=pending,
                summary=summary,
            )
        return summary

    # -- rotation cursor -------------------------------------------------

    def _sweep_window(self, *, batch: int) -> tuple[list[AIProposal], int, int, bool]:
        """The next window of the pending ring, wrapping when a pass ends.

        Returns the window, the ordinal it starts at, the size of the pending
        set, and whether the window opened a new pass. The wraparound is decided
        on read so a dry run can report what the next real run would do; only
        ``run(apply=True)`` writes the position back.
        """
        cursor = self._read_cursor()
        window, total = self._read_window(cursor=cursor, batch=batch)
        if window or cursor == 0:
            return window, cursor, total, False
        # The pass reached the tail of the pending set. Restart from the top in
        # the same run: those rows were examined a full pass ago, so the
        # rotation guarantee still holds, and the scheduled task never spends
        # its daily run on an empty window.
        window, total = self._read_window(cursor=0, batch=batch)
        return window, 0, total, True

    def _read_window(self, *, cursor: int, batch: int) -> tuple[list[AIProposal], int]:
        """The ``batch`` pending proposals after ``cursor``, and the set size.

        The cursor is an offset into this same ordering, which is only a stable
        position because the ordering is append-only: the evaluator marks its run
        succeeded and creates the proposal in the same transaction, so a row
        joins the pending set at the end and never behind the cursor. Rows leave
        the set when they are decided, and :meth:`_advance_cursor` keeps the
        offset correct for that. The offset is cheaper than loading the id of
        every pending proposal into Python, and works for a set of a few
        thousand rows; the only ids that are materialised are the window's, and
        only to count how many of them survive the pass.
        """
        pending = AIProposal.objects.filter(
            status=AIProposal.Status.PENDING,
            match_candidate__status=MatchCandidate.Status.PENDING,
            run__status="succeeded",
        )
        total = pending.count()
        window = list(
            pending.select_related(
                "run",
                "match_candidate__left_entity",
                "match_candidate__right_entity",
            ).order_by("created_at", "id")[cursor : cursor + batch]
        )
        return window, total

    def _advance_cursor(
        self,
        *,
        proposals: list[AIProposal],
        cursor: int,
        pending: int,
        summary: dict[str, Any],
    ) -> None:
        """Move the cursor past the rows this pass will not examine again.

        A decided proposal leaves the pending set, which pulls every row behind
        it one position towards the cursor, so the first proposal this pass did
        not examine now sits at ``cursor + survivors``. Survivors are counted in
        the database rather than derived from the summary counters because a
        candidate another process decided first closes a proposal without
        incrementing any of them.
        """
        survivors = AIProposal.objects.filter(
            pk__in=[proposal.pk for proposal in proposals],
            status=AIProposal.Status.PENDING,
        ).count()
        cursor_after = cursor + survivors
        summary["cursor_after"] = cursor_after
        self._write_cursor(
            cursor=cursor_after,
            total=max(0, pending - (len(proposals) - survivors)),
        )

    @staticmethod
    def _read_cursor() -> int:
        state = SyncState.objects.filter(
            task_name=ROTATION_TASK_NAME, shard=ROTATION_SHARD
        ).first()
        return int(state.current_id) if state is not None else 0

    @staticmethod
    def _write_cursor(*, cursor: int, total: int) -> None:
        SyncState.objects.update_or_create(
            task_name=ROTATION_TASK_NAME,
            shard=ROTATION_SHARD,
            defaults={
                "current_id": int(cursor),
                "end_id": int(total),
                "status": SyncState.Status.RUNNING,
            },
        )

    @staticmethod
    def reset_cursor() -> None:
        """Start the next pass from the top of the pending set."""
        SyncState.objects.filter(
            task_name=ROTATION_TASK_NAME, shard=ROTATION_SHARD
        ).update(current_id=0)

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
        if MatchApplyService._work_family_mismatch(candidate):
            reasons.append("work_family_mismatch")
        if MatchApplyService._release_years_conflict(candidate):
            reasons.append("release_year_conflict")
        if MatchApplyService._has_conflicting_user_library(candidate):
            reasons.append("conflicting_user_library")
        return reasons

    @staticmethod
    def _work_family_mismatch(candidate: MatchCandidate) -> bool:
        """Refuse works that are not the same kind of work.

        Only anime and galgame carry cross-provider identity, and a batch that
        runs unattended has no way to tell "the same work" from "the same kind of
        record" for anything else. A pair whose sides cannot be classified is
        refused rather than merged: this gate exists to fail closed.
        """
        types: dict[str, set[str]] = {}
        try:
            for side in ("left_entity", "right_entity"):
                cluster = entity_resolution_service.cluster_ids(
                    getattr(candidate, side)
                )
                types[side] = set(
                    Work.objects.filter(entity_id__in=cluster).values_list(
                        "work_type", flat=True
                    )
                )
        except (AttributeError, TypeError, ValueError, ObjectDoesNotExist):
            return True
        return not work_families.are_bindable(
            types["left_entity"], types["right_entity"]
        )

    @staticmethod
    def _release_years_conflict(candidate: MatchCandidate) -> bool:
        """Distinguish a duplicate from a remake.

        Two works whose premieres are years apart are different productions — a
        reboot, a remake, a second adaptation — and the titles being identical
        is exactly why a title-similarity candidate looks confident. Binding
        them silently rewrites the history of both.
        """
        from apps.index.models import AnimeProfile

        years = []
        for entity_id in (candidate.left_entity_id, candidate.right_entity_id):
            premiered = (
                AnimeProfile.objects.filter(work__entity_id=entity_id)
                .values_list("premiered_on", flat=True)
                .first()
            )
            if premiered is not None:
                years.append(premiered.year)
        if len(years) < 2:
            return False
        return abs(years[0] - years[1]) > RELEASE_YEAR_TOLERANCE

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
