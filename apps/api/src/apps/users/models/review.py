from django.db import models


class UserReview(models.Model):
    user_subject = models.ForeignKey(
        "UserLibraryEntry", on_delete=models.CASCADE, related_name="reviews"
    )
    title = models.CharField(max_length=256)
    content = models.TextField()
    is_public = models.BooleanField(default=True)
    is_spoiler = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_review"
        indexes = [
            models.Index(fields=["-created_at"], name="idx_review_created"),
            models.Index(fields=["-updated_at"], name="idx_review_updated"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.user_subject_id})"
