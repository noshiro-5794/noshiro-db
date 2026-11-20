"""Deliver queued verification messages while their database codes remain usable."""

from celery import shared_task

from api.db import fetch
from api.shared.mail import send_verification_code
from api.worker.runtime import run
from api.worker.session import session_scope


class MailDeliveryError(RuntimeError):
    """A verification email could not be accepted by the provider."""


async def deliver(verification_id: int) -> None:
    async with session_scope() as session:
        rows = await fetch(
            session,
            "SELECT email,code,purpose FROM email_verification "
            "WHERE id=:id AND NOT is_used AND expire_at>=clock_timestamp()",
            {"id": verification_id},
        )
    if not rows:
        return
    verification = rows[0]
    if not await send_verification_code(
        verification.email, verification.code, verification.purpose
    ):
        raise MailDeliveryError("Verification email delivery failed.")


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.users.tasks.email_tasks.send_verification_email",
    queue="realtime",
    autoretry_for=(MailDeliveryError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_kwargs={"max_retries": 3},
)
def send_verification_email(verification_id: int) -> None:
    run(deliver(verification_id))
