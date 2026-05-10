from django.db import transaction

from apps.users.models import User, UserProfile, EmailVerification
from apps.users.exceptions import EmailAlreadyExists
from apps.users.services.auth.verification_service import VerificationService

class RegisterService:

    @staticmethod
    def _check_email_exists(email: str) -> None:
        exists = User.objects.filter(email=email).exists()
        if exists:
            raise EmailAlreadyExists()

    @classmethod
    @transaction.atomic
    def register(cls, *, email: str, password: str, nickname: str, code: str) -> User:
        cls._check_email_exists(email)
        verification = VerificationService.verify_code(
            email=email, purpose=EmailVerification.Purpose.REGISTER, code=code
        )
        user = User.objects.create_user(email=email, password=password)
        UserProfile.objects.create(user=user, nickname=nickname)
        VerificationService.mark_as_used(verification)
        return user
