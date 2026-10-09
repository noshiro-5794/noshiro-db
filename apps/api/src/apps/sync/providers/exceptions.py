class ProviderAPIError(RuntimeError):
    """Base exception for external catalog provider failures."""

    retryable = False

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
        error_code: str = "provider_error",
        unavailable_reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
        self.error_code = error_code
        self.unavailable_reason = unavailable_reason

    @property
    def is_not_found(self) -> bool:
        """Whether the provider confirmed the record no longer exists.

        A retired id is a terminal answer, not a transient failure: retrying it
        can never succeed, so callers retire the work item instead of burning
        the retry budget. Providers that surface 404s without a status code can
        raise with ``error_code="not_found"``.
        """
        return self.status_code == 404 or self.error_code == "not_found"


class BangumiAPIError(ProviderAPIError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            retry_after=retry_after,
            error_code=f"http_{status_code}" if status_code else "request_error",
        )
        self.retryable = status_code == 429 or status_code is None or status_code >= 500


class VNDBAPIError(ProviderAPIError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            retry_after=retry_after,
            error_code=f"http_{status_code}" if status_code else "request_error",
        )
        self.retryable = status_code == 429 or status_code is None or status_code >= 500


class AniListAPIError(ProviderAPIError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
        unavailable_reason: str | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            retry_after=retry_after,
            error_code=f"http_{status_code}" if status_code else "request_error",
            unavailable_reason=unavailable_reason,
        )
        self.retryable = (
            unavailable_reason is not None
            or status_code == 429
            or status_code is None
            or status_code >= 500
        )


class MALAPIError(ProviderAPIError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            retry_after=retry_after,
            error_code=f"http_{status_code}" if status_code else "request_error",
        )
        self.retryable = status_code == 429 or status_code is None or status_code >= 500


__all__ = [
    "AniListAPIError",
    "BangumiAPIError",
    "MALAPIError",
    "ProviderAPIError",
    "VNDBAPIError",
]
