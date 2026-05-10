import time
import threading

from apps.sync.models import SyncState, SyncError
from apps.sync.tasks.progress import get_task_progress
from apps.sync.tasks.full_sync import (
    FullSubjectSyncTask,
    FullEpisodeSyncTask,
    FullSubjRelSyncTask,
    FullStfRelSyncTask,
    FullCharRelSyncTask,
    FullCharacterSyncTask,
    FullStaffSyncTask,
)


class SyncScheduler:

    TASKS = [
        ("full_subject",                    FullSubjectSyncTask),
        ("full_episode",                    FullEpisodeSyncTask),
        ("full_subject_subject_relation",   FullSubjRelSyncTask),
        ("full_subject_staff_relation",     FullStfRelSyncTask),
        ("full_subject_character_relation", FullCharRelSyncTask),
        ("full_character",                  FullCharacterSyncTask),
        ("full_staff",                      FullStaffSyncTask),
    ]

    PROGRESS_INTERVAL = 2

    def run_all(self, reset_tasks = None) -> None:
        print("=== SYNC START ===", flush=True)
        if reset_tasks:
            for task in reset_tasks:
                self._reset_task(task)
        started = False
        for name, task_cls in self.TASKS:
            states = SyncState.objects.filter(task_name=name)
            if not started:
                if states.exists() and all(s.status == "finished" for s in states):
                    print(f"=== SKIP {name} ===", flush=True)
                    continue
                else:
                    started = True
            self._run_phase(name, task_cls)
        print("=== SYNC FINISHED ===", flush=True)

    def _reset_task(self, task_name: str):
        print(f"=== RESET {task_name} ===", flush=True)

        SyncState.objects.filter(task_name=task_name).delete()
        SyncError.objects.filter(task_name=task_name).delete()

    def _run_phase(self, name, task_cls):
        print(f"\n=== START {name} ===", flush=True)
        start_time = time.time()

        stop_event = threading.Event()
        monitor = threading.Thread(
            target=self._progress_monitor,
            args=(name, stop_event),
            daemon=True,
        )
        monitor.start()
        try:
            task = task_cls()
            task.run_task()
        except Exception as e:
            print(f"!!! Error in {name}: {e}", flush=True)
            raise
        finally:
            stop_event.set()
            monitor.join()

        cost = time.time() - start_time
        print(f"=== END {name} | {cost:.2f}s ===", flush=True)
        time.sleep(2)

    def _progress_monitor(self, task_name, stop_event):
        while not stop_event.is_set():
            progress = get_task_progress(task_name)
            percent = progress["progress"] * 100
            print(f"[Progress][{task_name}] {percent:.2f}%", flush=True)
            time.sleep(self.PROGRESS_INTERVAL)
