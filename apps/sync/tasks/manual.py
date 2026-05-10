from apps.sync.services.subject_service import subject_service
from apps.sync.services.staff_service import staff_service
from apps.sync.services.character_service import character_service
from apps.sync.services.episode_service import episode_service
from apps.sync.services.relation_service import relation_service


class ManualSyncTask:

    @staticmethod
    def sync_subject(bangumi_id: int):
        subject_service.upsert_subject(bangumi_id)
        episode_service.sync_subject_episodes(bangumi_id)
        relations = relation_service.sync_all_relations(bangumi_id)
        ManualSyncTask._hydrate(relations)

    @staticmethod
    def _hydrate(relations: dict):
        for cid in relations["characters"]:
            character_service.upsert_character(int(cid))
        for sid in relations["staffs"]:
            staff_service.upsert_staff(int(sid))
