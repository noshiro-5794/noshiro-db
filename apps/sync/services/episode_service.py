from datetime import datetime, date, timedelta
from django.db import transaction

from apps.index.models import Subject, Episode
from apps.sync.providers.bangumi import bangumi_client
from apps.sync.services.subject_service import subject_service


class EpisodeService:

    INFO_SOURCE = "bangumi_episode"

    def sync_subject_episodes(self, bangumi_id: int) -> None:
        subject = subject_service.provide_subject(bangumi_id)
        limit = 100
        offset = 0
        while True:
            resp = bangumi_client.fetch_subject_episodes(
                subject_id=bangumi_id,
                limit=limit,
                offset=offset,
            )
            data = resp.get("data")
            if not isinstance(data, list):
                break
            if len(data) == 0:
                break
            self._upsert_episodes(subject, data)
            if len(data) < limit:
                break
            offset += limit

    def _upsert_episodes(self, subject: Subject, data: list[dict]) -> None:
        if not data:
            return

        id_map = {}
        for item in data:
            bangumi_id = item.get("id")
            if not bangumi_id:
                continue
            id_map[str(bangumi_id)] = item
        if not id_map:
            return
        ids = list(id_map.keys())

        existing_qs = Episode.objects.filter(
            info_source=self.INFO_SOURCE,
            id_source__in=ids,
        )
        existing_map = {obj.id_source: obj for obj in existing_qs}
        to_create = []
        to_update = []

        for id_source, item in id_map.items():
            mapped = self._map_episode_data(item)
            if id_source in existing_map:
                obj = existing_map[id_source]

                for field, value in mapped.items():
                    setattr(obj, field, value)
                obj.subject = subject

                to_update.append(obj)
            else:
                obj = Episode(
                    info_source=self.INFO_SOURCE,
                    id_source=id_source,
                    subject=subject,
                    **mapped,
                )
                to_create.append(obj)

        with transaction.atomic():
            if to_create:
                Episode.objects.bulk_create(to_create, batch_size=100)
            if to_update:
                Episode.objects.bulk_update(
                    to_update,
                    fields=[
                        "title",
                        "type",
                        "ep_num",
                        "sort",
                        "duration",
                        "date",
                        "description",
                        "subject",
                    ],
                    batch_size=100,
                )

    def _map_episode_data(self, data: dict) -> dict:
        return {
            "title":        self._parse_episode_title(data),
            "type":         self._parse_episode_type(data),
            "ep_num":       self._parse_episode_ep_num(data),
            "sort":         self._parse_episode_sort(data),
            "duration":     self._parse_episode_duration(data),
            "date":         self._parse_episode_air_date(data),
            "description":  self._parse_episode_description(data),
        }

    def _parse_episode_title(self, data: dict) -> str:
        title = data.get("name")
        return title.strip() if isinstance(title, str) else ""

    def _parse_episode_type(self, data: dict) -> str:
        episode_type_mapping = {
            0: "EP",
            1: "SP",
            2: "OP",
            3: "ED",
            4: "PV/CM",
            5: "MAD",
            6: "ETC",
        }
        t = data.get("type")
        if not isinstance(t, int):
            return ""
        return episode_type_mapping.get(t) if t in episode_type_mapping else ""

    def _parse_episode_ep_num(self, data: dict) -> int | None:
        ep_num = data.get("ep")
        return ep_num if isinstance(ep_num, int) else None

    def _parse_episode_sort(self, data: dict) -> int | None:
        sort = data.get("sort")
        return sort if isinstance(sort, int) else None

    def _parse_episode_duration(self, data: dict) -> timedelta | None:
        duration = data.get("duration_seconds")
        if not isinstance(duration, int):
            return None
        if duration <= 0:
            return None
        return timedelta(seconds=duration)

    def _parse_episode_air_date(self, data: dict) -> date | None:
        fmt = "%Y-%m-%d"
        value = data.get("airdate")
        if not isinstance(value, str):
            return None
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            return None

    def _parse_episode_description(self, data: dict) -> str:
        description = data.get("desc")
        return description.strip() if isinstance(description, str) else ""


episode_service = EpisodeService()
