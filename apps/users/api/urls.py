from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.api.views import (
    SendCodeView,
    RegisterView,
    PasswordLoginView,
    CodeLoginView,
    ResetPasswordView,
)

urlpatterns = [
    path("send-code/", SendCodeView.as_view(), name="send-code"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/password/", PasswordLoginView.as_view(), name="password-login"),
    path("login/code/", CodeLoginView.as_view(), name="code-login"),
    path("password/reset/", ResetPasswordView.as_view(), name="reset-password"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
