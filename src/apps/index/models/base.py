from django.db import models


class ContentSafety(models.TextChoices):
    SAFE = "safe", "Safe"
    SUGGESTIVE = "suggestive", "Suggestive"
    EXPLICIT = "explicit", "Explicit"
    UNKNOWN = "unknown", "Unknown"


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
