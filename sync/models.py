from django.db import models


class NameMapping(models.Model):

    external_name   = models.CharField(max_length=256)
    internal_name   = models.CharField(max_length=256)

    class Meta:
        db_table = 'name_mapping'
        constraints = [
            models.UniqueConstraint(fields=["external_name"], name="uq_name_mapping"),
        ]
        indexes = [
            models.Index(fields=["external_name"], name="idx_name_mapping"),
        ]

    def __str__(self):
        return f"{self.external_name} -> {self.internal_name}"


class SyncState(models.Model):

    SOURCE_CHOICES = [
        ("bangumi", "Bangumi"),
        ("mal",     "MyAnimeList"),
        ("vndb",    "VNDB"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed",  "Failed"),
    ]

    source = models.CharField(max_length=64, choices=SOURCE_CHOICES)
    entity_type = models.CharField(max_length=64)
    external_id = models.CharField(max_length=64)
    status = models.CharField(max_length=64, choices=STATUS_CHOICES, default="pending")
    last_synced = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sync_state'
        indexes = [
            models.Index(fields=["source", "entity_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"{self.source}:{self.entity_type}:{self.external_id} [{self.status}]"

class GenreMapping(models.Model):

    SOURCE_CHOICES = [
        ("bangumi", "Bangumi"),
        ("mal", "MyAnimeList"),
        ("vndb", "VNDB"),
    ]

    source = models.CharField(max_length=64, choices=SOURCE_CHOICES)
    external_genre = models.CharField(max_length=256)
    internal_genre = models.CharField(max_length=256)

    class Meta:
        db_table = 'genre_mapping'
        constraints = [
            models.UniqueConstraint(fields=["source", "external_genre"], name="uq_genre_mapping_external"),
        ]
        indexes = [
            models.Index(fields=["source", "external_genre"], name="idx_genre_mapping_external"),
        ]

    def __str__(self):
        return f"{self.source}: {self.external_genre} -> {self.internal_genre}"
