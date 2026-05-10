from django.db import models


class NameMapping(models.Model):

    external_name   = models.CharField(max_length=256)
    internal_name   = models.CharField(max_length=256)

    class Meta:
        db_table = "name_mapping"
        constraints = [
            models.UniqueConstraint(fields=["external_name"], name="uq_name_mapping"),
        ]
        indexes = [
            models.Index(fields=["external_name"], name="idx_name_mapping"),
        ]

    def __str__(self):
        return f"{self.external_name} -> {self.internal_name}"


class SyncState(models.Model):

    task_name   = models.CharField(max_length=256)
    shard       = models.CharField(max_length=256)
    current_id  = models.IntegerField(default=0)
    end_id      = models.IntegerField()
    status      = models.CharField(max_length=256, default="running")
    fail_count  = models.IntegerField(default=0)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sync_state"
        constraints = [
            models.UniqueConstraint(fields=["task_name", "shard"], name="uq_name_shard")
        ]
        indexes = [
            models.Index(fields=["task_name", "shard"], name="idx_name_shard")
        ]

    def __str__(self):
        return f"{self.task_name}:{self.current_id} [{self.status}]"


class SyncError(models.Model):

    task_name           = models.CharField(max_length=256)
    entity_id           = models.IntegerField()
    retry_count         = models.IntegerField(default=1)
    first_occurred_at   = models.DateTimeField(auto_now_add=True)
    last_occurred_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sync_error"
        constraints = [
            models.UniqueConstraint(fields=["task_name", "entity_id"], name="uq_name_id")
        ]
        indexes = [
            models.Index(fields=["task_name", "entity_id"], name="idx_name_id"),
        ]

    def __str__(self):
        return f"{self.task_name}:{self.entity_id}"
