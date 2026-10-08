def _default_retryable(status_code: int | None) -> bool:
    """Whether trying the same request again could plausibly work.

    A missing status means the request never produced an answer — a timeout, a
    dropped connection — which is worth another attempt. 429 and 5xx are the
    provider asking us to wait. Everything else in the 4xx range is our fault
    or the account's, and repeating it only wastes a call: 402 in particular
    means the balance is gone, which no amount of retrying fixes.
    """
    if status_code is None:
        return True
    if status_code == 429:
        return True
    return status_code >= 500


class AIProviderError(RuntimeError):
    """Raised when an AI provider request or response cannot be completed."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = (
            _default_retryable(status_code) if retryable is None else retryable
        )

    @property
    def is_account_problem(self) -> bool:
        """The account cannot call the provider until someone acts on it."""
        return self.status_code in {401, 402, 403}
