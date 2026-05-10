from datetime import datetime, date
from django.db import transaction, IntegrityError

from apps.index.models import Subject
from apps.sync.providers.bangumi import bangumi_client
from apps.sync.services.name_normalizer import name_normalizer


class SubjectService:

    INFO_SOURCE = "bangumi_subject"

    def upsert_subject(self, bangumi_id: int) -> Subject | None:
        data = bangumi_client.fetch_subject(bangumi_id)
        if not data:
            return None
        mapped_data = self._map_subject_data(data)
        try:
            with transaction.atomic():
                subject, _ = Subject.objects.update_or_create(
                    info_source=self.INFO_SOURCE,
                    id_source=str(bangumi_id),
                    defaults=mapped_data,
                )
        except IntegrityError:
            return Subject.objects.get(
                info_source=self.INFO_SOURCE,
                id_source=str(bangumi_id),
            )
        return subject

    def provide_subject(self, bangumi_id: int) -> Subject:
        try:
            with transaction.atomic():
                subject, _ = Subject.objects.get_or_create(
                    info_source=self.INFO_SOURCE,
                    id_source=str(bangumi_id),
                )
                return subject
        except IntegrityError:
            return Subject.objects.get(
                info_source=self.INFO_SOURCE,
                id_source=str(bangumi_id),
            )

    def _map_subject_data(self, data: dict) -> dict:
        return {
            "subject_type":     self._parse_subject_type(data),
            "title":            self._parse_subject_title(data),
            "title_cn":         self._parse_subject_title_cn(data),
            "date":             self._parse_subject_date(data),
            "image_original":   self._parse_subject_image_original(data),
            "image_thumbnail":  self._parse_subject_image_thumbnail(data),
            "platform":         self._parse_subject_platform(data),
            "description":      self._parse_subject_description(data),
            "nsfw":             self._parse_subject_nsfw(data),
            "series":           self._parse_subject_series(data),
            "volumes":          self._parse_subject_volumes(data),
            "eps":              self._parse_subject_eps(data),
            "total_episodes":   self._parse_subject_total_episodes(data),
            "infobox":          self._parse_subject_infobox(data),
            "tags":             self._parse_subject_tags(data),
        }

    def _parse_subject_type(self, data: dict) -> str:
        type_id = data.get("type")
        if not isinstance(type_id, int):
            return "other"
        type_mapping = {
            1: lambda: self._parse_subject_type_book(data),
            2: lambda: "anime",
            3: lambda: "music",
            4: lambda: self._parse_subject_type_game(data),
            6: lambda: "other",
        }
        return type_mapping.get(type_id, lambda: "other")()

    def _parse_subject_type_book(self, data: dict) -> str:
        platform = data.get("platform")
        if isinstance(platform, str):
            if "小说" in platform:
                return "novel"
            elif "漫画" in platform:
                return "manga"
        return "book"

    def _parse_subject_type_game(self, data: dict) -> str:
        metatag = data.get("metatag")
        if isinstance(metatag, list):
            for tag in metatag:
                if isinstance(tag, str) and tag.lower() == "galgame":
                    return "galgame"
        return "game"

    def _parse_subject_title(self, data: dict) -> str:
        title = data.get("name")
        return title.strip() if isinstance(title, str) else ""

    def _parse_subject_title_cn(self, data: dict) -> str:
        title_cn = data.get("name_cn")
        return title_cn.strip() if isinstance(title_cn, str) else ""

    def _parse_subject_date(self, data: dict) -> date | None:
        fmt = "%Y-%m-%d"
        value = data.get("date")
        if not isinstance(value, str):
            return None
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            return None

    def _parse_subject_image_original(self, data: dict) -> str:
        images = data.get("images")
        if not isinstance(images, dict):
            return ""
        url = images.get("large")
        return url.strip() if isinstance(url, str) else ""

    def _parse_subject_image_thumbnail(self, data: dict) -> str:
        images = data.get("images")
        if not isinstance(images, dict):
            return ""
        url = images.get("medium")
        return url.strip() if isinstance(url, str) else ""

    def _parse_subject_platform(self, data: dict) -> str:
        platform = data.get("platform")
        return (
            name_normalizer.normalize_name(platform.strip())
            if isinstance(platform, str)
            else ""
        )

    def _parse_subject_description(self, data: dict) -> str:
        description = data.get("summary")
        return description.strip() if isinstance(description, str) else ""

    def _parse_subject_nsfw(self, data: dict) -> bool:
        nsfw = data.get("nsfw")
        return nsfw if isinstance(nsfw, bool) else False

    def _parse_subject_series(self, data: dict) -> bool:
        series = data.get("series")
        return series if isinstance(series, bool) else False

    def _parse_subject_volumes(self, data: dict) -> int | None:
        volumes = data.get("volumes")
        return volumes if isinstance(volumes, int) else None

    def _parse_subject_eps(self, data: dict) -> int | None:
        eps = data.get("eps")
        return eps if isinstance(eps, int) else None

    def _parse_subject_total_episodes(self, data: dict) -> int | None:
        total_episodes = data.get("total_episodes")
        return total_episodes if isinstance(total_episodes, int) else None

    def _parse_subject_infobox(self, data: dict) -> list:
        infobox = data.get("infobox")
        if not isinstance(infobox, list):
            return []
        result = []
        for item in infobox:
            parsed = self._parse_infobox_item(item)
            if parsed:
                result.append(parsed)
        return result

    def _parse_infobox_item(self, item: dict) -> dict | None:
        if not isinstance(item, dict):
            return None
        key = item.get("key")
        normalized_key = ""
        if isinstance(key, str):
            normalized_key = name_normalizer.normalize_name(key.strip())
        value = item.get("value")
        normalized_value = self._normalize_infobox_value(value)
        if not normalized_key and not normalized_value:
            return None
        return {"key": normalized_key, "value": normalized_value}

    def _normalize_infobox_value(self, value) -> list:
        result: list[str] = []
        if isinstance(value, str):
            result.append(value.strip())
            return result
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    v = item.get("v")
                    if isinstance(v, str):
                        result.append(v.strip())
            return result
        return []

    def _parse_subject_tags(self, data: dict) -> list:
        tags = data.get("meta_tags")
        if not isinstance(tags, list):
            return []
        result = []
        for tag in tags:
            if isinstance(tag, str):
                normalized = name_normalizer.normalize_name(tag.strip())
                if normalized:
                    result.append(normalized)
        return result


subject_service = SubjectService()
