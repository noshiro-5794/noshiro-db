from django.contrib.auth import authenticate

from apps.users.models import User, EmailVerification
from apps.users.exceptions import InvalidEmailOrPassword, UserNotFound
from apps.users.services.auth.verification_service import VerificationService


class LoginService:

    @classmethod
    def password_login(cls, *, email: str, password: str) -> User:
        user = authenticate(username=email, password=password)
        if not user:
            raise InvalidEmailOrPassword()
        return user

    @classmethod
    def code_login(cls, *, email: str, code: str) -> User:
        verification = VerificationService.verify_code(
            email=email, purpose=EmailVerification.Purpose.LOGIN, code=code
        )
        user = User.objects.filter(email=email).first()
        if not user:
            raise UserNotFound()
        VerificationService.mark_as_used(verification)
        return user
