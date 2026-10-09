import uuid

from django.db import models


class AgentMessage(models.Model):
    """One append-only transcript event inside an agent run.

    The transcript is the source of truth for an open-ended agent loop: it is
    replayed verbatim when a run pauses, resumes, or moves to another worker.
    ``tool_calls`` only exists on ``assistant`` rows; ``tool_call_id`` and
    ``name`` only exist on ``tool`` rows.
    """

    class Role(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        TOOL = "tool", "Tool"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        "AgentRun",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sequence = models.PositiveIntegerField()
    role = models.CharField(max_length=16, choices=Role.choices)
    name = models.CharField(max_length=128, blank=True)
    tool_call_id = models.CharField(max_length=128, blank=True)
    content = models.TextField(blank=True)
    tool_calls = models.JSONField(default=list, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_message"
        ordering = ["run", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "sequence"], name="uq_agent_message_run_sequence"
            )
        ]
        indexes = [
            models.Index(fields=["run", "sequence"], name="idx_agent_message_run_seq")
        ]

    def __str__(self) -> str:
        return f"{self.run_id}:{self.sequence} {self.role}"
