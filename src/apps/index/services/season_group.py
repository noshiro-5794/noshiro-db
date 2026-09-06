"""Season-group persistence for same-series, different-granularity entries."""

from __future__ import annotations

import hashlib

from apps.index.models import Entity, EntityName, IndexCollection, IndexMembership


class SeasonGroupService:
    def ensure_pair_group(
        self,
        *,
        left: Entity,
        right: Entity,
        reason: str = "provider-granularity",
    ) -> IndexCollection:
        """Create or reuse a group that lists two distinct granularity entries."""
        if left.pk == right.pk:
            raise ValueError("Season group requires two distinct entities.")
        originals = [
            text
            for entity in (left, right)
            if (
                text := EntityName.objects.filter(
                    entity=entity,
                    kind=EntityName.Kind.ORIGINAL,
                )
                .values_list("text", flat=True)
                .first()
            )
        ]
        key_material = "|".join(sorted(originals)).lower().strip()
        digest = hashlib.sha1(key_material.encode()).hexdigest()[:12]
        collection, _ = IndexCollection.objects.get_or_create(
            slug=f"season-group-{digest}",
            defaults={
                "name": f"同季分组 {originals[0][:100]}" if originals else "同季分组",
            },
        )
        for entity in (left, right):
            IndexMembership.objects.get_or_create(
                collection=collection,
                entity=entity,
                defaults={
                    "listing_state": IndexMembership.State.LISTED,
                    "inclusion_reason": reason,
                },
            )
        return collection


season_group_service = SeasonGroupService()
