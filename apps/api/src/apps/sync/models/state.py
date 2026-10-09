from django.db import models


class SyncState(models.Model):
    class Status(models.TextChoices):
        IDLE = "idle", "Idle"
        RUNNING = "running", "Running"
        FINISHED = "finished", "Finished"
        FAILED = "failed", "Failed"

    task_name = models.CharField(max_length=256)
    shard = models.CharField(max_length=256)
    current_id = models.PositiveIntegerField(default=0)
    end_id = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    fail_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sync_state"
        constraints = [
            models.UniqueConstraint(fields=["task_name", "shard"], name="uq_name_shard")
        ]

    def __str__(self) -> str:
        return f"{self.task_name}:{self.current_id} [{self.status}]"


class SyncError(models.Model):
    task_name = models.CharField(max_length=256)
    entity_id = models.IntegerField()
    retry_count = models.PositiveIntegerField(default=1)
    first_occurred_at = models.DateTimeField(auto_now_add=True)
    last_occurred_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sync_error"
        constraints = [
            models.UniqueConstraint(
                fields=["task_name", "entity_id"], name="uq_name_id"
            )
        ]

    def __str__(self) -> str:
        return f"{self.task_name}:{self.entity_id}"
