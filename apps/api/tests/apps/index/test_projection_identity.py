import uuid

import pytest

from apps.index.models import (
    Entity,
    EntityName,
    EntityRedirect,
    MergeEvent,
)
from apps.index.selectors.projections import entity_detail
from apps.index.services import season_group_service

pytestmark = pytest.mark.django_db(transaction=True)


def _work(text: str) -> Entity:
    entity = Entity.objects.create(kind=Entity.Kind.WORK)
    EntityName.objects.create(
        entity=entity,
        text=text,
        language="ja",
        kind=EntityName.Kind.ORIGINAL,
    )
    return entity


def test_detail_exposes_season_group_memberships() -> None:
    left = _work("Re:Zero 4th season")
    right = _work("Re:ゼロから始める異世界生活 4th season 奪還編")
    season_group_service.ensure_pair_group(left=left, right=right)

    data = entity_detail(right, safe=True)

    assert any(
        item["collection"].startswith("season-group-") for item in data["memberships"]
    )
    assert data["collections"]
    assert data["is_merged"] is False


def test_detail_exposes_merged_source_aliases() -> None:
    source = _work("旧无职转生条目")
    target = _work("Mushoku Tensei 3rd Season")
    event = MergeEvent.objects.create(
        source_entity=source,
        target_entity=target,
        method=MergeEvent.Method.RULE,
        reason="test",
        snapshot={},
    )
    EntityRedirect.objects.create(
        source_entity=source,
        target_entity=target,
        merge_event=event,
    )
    source.lifecycle = Entity.Lifecycle.MERGED
    source.save(update_fields=["lifecycle"])

    data = entity_detail(target, safe=True)

    assert data["is_merged"] is True
    assert {uuid.UUID(row["entity_id"]) for row in data["merged_from"]} == {source.pk}
