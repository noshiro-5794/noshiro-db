"""Provider failures, classified by what the caller should do about them.

The distinction that matters everywhere downstream is *terminal* versus *transient*: a
404 is an answer and the work item should be retired, while a 429 or a timeout says try
again later. Collapsing the two either burns the retry budget on ids that will never
resolve, or retires a record because the provider was briefly down.
"""

from __future__ import annotations


class ProviderError(RuntimeError):
    """An external catalogue provider refused or failed a request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
        error_code: str = "provider_error",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
        self.error_code = error_code

    @property
    def is_not_found(self) -> bool:
        """Whether the provider confirmed the record does not exist."""
        return self.status_code == 404 or self.error_code == "not_found"

    @property
    def retryable(self) -> bool:
        """Whether waiting and asking again could succeed."""
        if self.is_not_found:
            return False
        if self.status_code is None:
            return self.error_code in {"transport_error", "invalid_json"}
        return self.status_code == 429 or self.status_code >= 500


def retry_after_seconds(headers: object) -> float | None:
    """The provider's own back-off hint, when it gave one."""
    value = getattr(headers, "get", lambda *_: None)("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


__all__ = ["ProviderError", "retry_after_seconds"]
