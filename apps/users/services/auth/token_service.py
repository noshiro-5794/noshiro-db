from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User


class TokenService:

    @staticmethod
    def create_tokens(user: User) -> dict:
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
