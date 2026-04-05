import threading
from typing import Callable

from sync.models import SyncState
from sync.tasks.progress import ProgressRecorder


class BaseSyncTask:

    TASK_NAME = None
    MAX_WORKERS = 5
    SHARD_SIZE = 16384
    MAX_RETRY = 3
    REFRESH_INTERVAL = 50

    def run(self, handler: Callable[[int], None], start: int, end: int) -> None:
        shards = self._build_shards(start, end)

        threads = []
        for shard in shards:
            t = threading.Thread(
                target=self._run_shard,
                args=(handler, shard),
                daemon=True,
            )
            t.start()
            threads.append(t)

            if len(threads) >= self.MAX_WORKERS:
                self._wait(threads)
                threads = []

        self._wait(threads)

    def _run_shard(self, handler, shard: tuple[int, int]) -> None:
        start, end = shard
        shard_name = f"{start}-{end}"

        state, _ = SyncState.objects.get_or_create(
            task_name=self.TASK_NAME,
            shard=shard_name,
            defaults={
                "current_id": start,
                "end_id": end,
                "status": "running",
            },
        )

        recorder = ProgressRecorder(self.TASK_NAME, shard_name)

        current = max(state.current_id, start)
        step = 0

        while current <= end:

            if step % self.REFRESH_INTERVAL == 0:
                state.refresh_from_db()
                if state.status != "running":
                    return

            success = self._safe_handle(handler, current)

            if success:
                recorder.record_success()
            else:
                recorder.record_fail(current)

            current += 1
            step += 1

            recorder.flush(current)

        recorder.finish(current)

    def _safe_handle(self, handler: Callable[[int], None], id_: int) -> bool:
        for _ in range(self.MAX_RETRY):
            try:
                handler(id_)
                return True
            except Exception:
                continue
        return False

    def _build_shards(self, start: int, end: int):
        shards = []
        cur = start

        while cur <= end:
            shard_end = min(cur + self.SHARD_SIZE - 1, end)
            shards.append((cur, shard_end))
            cur = shard_end + 1

        return shards

    def _wait(self, threads):
        for t in threads:
            t.join()
