from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.ai.services.common import validate_matching_output
from apps.index.models import (
    Entity,
    EntityName,
    IndexCollection,
    IndexMembership,
    MatchCandidate,
)
from apps.index.services import season_group_service

pytestmark = pytest.mark.django_db(transaction=True)


def test_validate_matching_output_accepts_group() -> None:
    output = validate_matching_output(
        {
            "decision": "group",
            "confidence": 0.9,
            "reason": "same season split into cours",
        }
    )
    assert output["decision"] == "group"


def _candidate() -> tuple[MatchCandidate, Entity, Entity]:
    left = Entity.objects.create(kind=Entity.Kind.WORK)
    right = Entity.objects.create(kind=Entity.Kind.WORK)
    EntityName.objects.create(
        entity=left,
        text="Re:Zero 4th season",
        language="en",
        kind=EntityName.Kind.ORIGINAL,
    )
    EntityName.objects.create(
        entity=right,
        text="Re:ゼロから始める異世界生活 4th season 奪還編",
        language="ja",
        kind=EntityName.Kind.ORIGINAL,
    )
    candidate = MatchCandidate.objects.create(
        left_entity=left,
        right_entity=right,
        policy_version="title-similarity-v1",
        score=Decimal("0.8700"),
        runner_up_margin=Decimal("0.1000"),
        status=MatchCandidate.Status.PENDING,
        hard_conflicts=[],
    )
    return candidate, left, right


def test_season_group_is_idempotent_and_lists_both_entities() -> None:
    _candidate()
    left = Entity.objects.filter(kind=Entity.Kind.WORK).first()
    right = Entity.objects.filter(kind=Entity.Kind.WORK).last()

    first = season_group_service.ensure_pair_group(left=left, right=right)
    second = season_group_service.ensure_pair_group(left=left, right=right)

    assert first.pk == second.pk
    assert IndexCollection.objects.count() == 1
    assert IndexMembership.objects.filter(collection=first).count() == 2


def test_admin_group_decision_creates_group_without_merging() -> None:
    candidate, left, right = _candidate()
    user = get_user_model().objects.create_user(
        "admin@example.test", "x", is_staff=True
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f"/api/v1/operations/matching/candidates/{candidate.pk}/decide/",
        {"outcome": "group", "reason": "whole season vs cour"},
        format="json",
    )

    assert response.status_code == 200
    candidate.refresh_from_db()
    assert candidate.status == MatchCandidate.Status.GROUPED
    collection = IndexCollection.objects.get()
    assert {member.entity_id for member in collection.memberships.all()} == {
        left.pk,
        right.pk,
    }
    assert left.lifecycle == Entity.Lifecycle.ACTIVE
    assert right.lifecycle == Entity.Lifecycle.ACTIVE
