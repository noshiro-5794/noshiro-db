"""Rotating refresh of the Bangumi subjects we already know.

Bangumi publishes no "changed since" feed, so the only way to notice that a
title, episode count or rating moved is to re-fetch records we already hold.
The id-space sweep covers records we have never seen; this service covers the
other half, oldest first.

It doubles as the legacy backfill. A record still stored as ``legacy`` carries
no raw payload and no revision, so re-fetching it is also what promotes it onto
the modern ``provider_record -> revision -> observation`` form. Legacy rows are
therefore refreshed first, and the result reports how many were promoted.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db.models import F

from apps.index.models import IndexMembership, ProviderRecord
from apps.sync.models import SyncError
from apps.sync.providers.bangumi import BANGUMI_SOURCE, BangumiAPIError
from apps.sync.services.subject import subject_service

logger = logging.getLogger(__name__)


class SubjectRefreshService:
    TASK_NAME = "bangumi_subject_refresh"
    MAX_LIMIT = 20000

    def refresh(
        self,
        *,
        limit: int,
        catalogue_only: bool = True,
    ) -> dict[str, Any]:
        """Re-fetch up to ``limit`` known subjects, legacy rows first."""
        bounded = max(1, min(int(limit), self.MAX_LIMIT))
        targets = self.select_targets(limit=bounded, catalogue_only=catalogue_only)
        result: dict[str, Any] = {
            "task_name": self.TASK_NAME,
            "limit": bounded,
            "catalogue_only": catalogue_only,
            "selected": len(targets),
            "legacy_selected": sum(
                1
                for record in targets
                if record.raw_state == ProviderRecord.RawState.LEGACY
            ),
            "refreshed": 0,
            "promoted": 0,
            "missing": 0,
            "skipped": 0,
            "failed": 0,
        }
        for record in targets:
            was_legacy = record.raw_state == ProviderRecord.RawState.LEGACY
            try:
                external_id = int(record.external_id)
            except (TypeError, ValueError):
                result["skipped"] += 1
                continue
            try:
                subject_service.upsert_subject(external_id)
            except BangumiAPIError as exc:
                if exc.is_not_found:
                    # A direct fetch answering 404 is authoritative: the subject
                    # is gone. A later successful fetch flips it back to active.
                    ProviderRecord.objects.filter(pk=record.pk).update(
                        status=ProviderRecord.Status.MISSING
                    )
                    result["missing"] += 1
                    continue
                result["failed"] += 1
                self._record_error(external_id)
                continue
            except Exception:
                logger.exception(
                    "Bangumi subject refresh failed",
                    extra={"external_id": record.external_id},
                )
                result["failed"] += 1
                self._record_error(external_id)
                continue
            result["refreshed"] += 1
            if was_legacy:
                result["promoted"] += 1
        return result

    def _record_error(self, bangumi_id: int) -> None:
        error, created = SyncError.objects.get_or_create(
            task_name=self.TASK_NAME,
            entity_id=bangumi_id,
        )
        if not created:
            SyncError.objects.filter(pk=error.pk).update(
                retry_count=F("retry_count") + 1,
            )

    @staticmethod
    def select_targets(
        *,
        limit: int,
        catalogue_only: bool = True,
    ) -> list[ProviderRecord]:
        """Legacy rows first, then whatever was refreshed longest ago."""
        base = ProviderRecord.objects.filter(
            namespace__provider__slug=BANGUMI_SOURCE.slug,
            namespace__slug="subject",
            status=ProviderRecord.Status.ACTIVE,
        )
        if catalogue_only:
            # Only records behind a work the catalogue actually lists: spending
            # the budget on the deep tail would leave the entries a visitor can
            # reach still stored as legacy rows. A merely *represented* record is
            # not enough — most of those are not in a collection.
            base = base.filter(
                representations__is_active=True,
                representations__entity__index_memberships__listing_state=(
                    IndexMembership.State.LISTED
                ),
            ).distinct()
        order = (F("last_seen_at").asc(nulls_first=True), "external_id")
        legacy = list(
            base.filter(raw_state=ProviderRecord.RawState.LEGACY)
            .order_by(*order)
            .only("id", "external_id", "raw_state", "last_seen_at")[:limit]
        )
        remaining = limit - len(legacy)
        if remaining <= 0:
            return legacy
        fresh = list(
            base.exclude(raw_state=ProviderRecord.RawState.LEGACY)
            .order_by(*order)
            .only("id", "external_id", "raw_state", "last_seen_at")[:remaining]
        )
        return legacy + fresh


subject_refresh_service = SubjectRefreshService()


__all__ = ["SubjectRefreshService", "subject_refresh_service"]
