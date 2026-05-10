from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.core.response import success_response
from apps.users.services.auth.login_service import LoginService
from apps.users.services.auth.token_service import TokenService
from apps.users.services.auth.password_service import PasswordService
from apps.users.services.auth.register_service import RegisterService
from apps.users.services.auth.verification_service import VerificationService
from apps.users.api.serializers import (
    SendCodeSerializer,
    RegisterSerializer,
    PasswordLoginSerializer,
    CodeLoginSerializer,
    ResetPasswordSerializer,
)


class SendCodeView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        VerificationService.send_code(
            email=serializer.validated_data["email"],
            purpose=serializer.validated_data["purpose"],
        )
        return success_response(message="verification code sent")


class RegisterView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = RegisterService.register(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            nickname=serializer.validated_data["nickname"],
            code=serializer.validated_data["code"],
        )
        tokens = TokenService.create_tokens(user)
        return success_response(data=tokens, message="register success")


class PasswordLoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = LoginService.password_login(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        tokens = TokenService.create_tokens(user)
        return success_response(data=tokens, message="login success")


class CodeLoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CodeLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = LoginService.code_login(
            email=serializer.validated_data["email"],
            code=serializer.validated_data["code"],
        )
        tokens = TokenService.create_tokens(user)
        return success_response(data=tokens, message="login success")


class ResetPasswordView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PasswordService.reset_password(
            email=serializer.validated_data["email"],
            code=serializer.validated_data["code"],
            new_password=serializer.validated_data["new_password"],
        )
        return success_response(message="password reset success")
