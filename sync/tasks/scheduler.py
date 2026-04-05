import time

from sync.tasks.full_sync import (
    FullSubjectSyncTask,
    FullEpisodeSyncTask,
    FullSubjRelSyncTask,
    FullStfRelSyncTask,
    FullCharRelSyncTask,
    FullCharacterSyncTask,
    FullStaffSyncTask,
)


class SyncScheduler:

    def run_all(self):
        print("=== SYNC START ===")

        self._run_phase("Subject", FullSubjectSyncTask)
        self._run_phase("Episode", FullEpisodeSyncTask)
        self._run_phase("Subject Relation", FullSubjRelSyncTask)
        self._run_phase("Staff Relation", FullStfRelSyncTask)
        self._run_phase("Character Relation", FullCharRelSyncTask)
        self._run_phase("Character", FullCharacterSyncTask)
        self._run_phase("Staff", FullStaffSyncTask)

        print("=== SYNC FINISHED ===")

    def _run_phase(self, name, task_cls):
        print(f"\n=== START {name} ===")

        start = time.time()

        task = task_cls()
        task.run_task()

        cost = time.time() - start
        print(f"=== END {name} | {cost:.2f}s ===")

        time.sleep(3)
