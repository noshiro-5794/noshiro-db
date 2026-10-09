"""Third-party sign-in endpoints (see ``services.auth.social_service``)."""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpResponseRedirect
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.api.serializers.social import (
    SocialAuthorizeSerializer,
    SocialProviderSerializer,
)
from apps.users.exceptions import InvalidSocialState
from apps.users.services.auth.social import (
    GitHubOAuthClient,
    social_login_service,
)
from apps.users.services.auth.token import TokenService
from shared.api.contracts import api_responses
from shared.exceptions import ApplicationError

logger = logging.getLogger(__name__)


def safe_redirect_path(value: str) -> str:
    """Accept only in-site absolute paths as post-login destinations.

    Anything absolute (``https://evil.test``) or protocol-relative
    (``//evil.test``) is dropped, so the callback cannot be turned into an open
    redirect.
    """
    if not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


class SocialProviderListView(APIView):
    """Which social sign-in buttons the frontend should render."""

    permission_classes = [AllowAny]

    @extend_schema(
        responses=api_responses({200: SocialProviderSerializer(many=True)}, errors=())
    )
    def get(self, request):
        return Response(
            [
                {
                    "provider": "github",
                    "enabled": GitHubOAuthClient().is_configured,
                    "authorize_path": "/api/v1/auth/social/github/start/",
                }
            ]
        )


class GitHubLoginStartView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth_login"

    @extend_schema(
        parameters=[
            OpenApiParameter("redirect", OpenApiTypes.STR, required=False),
        ],
        responses=api_responses({200: SocialAuthorizeSerializer}, errors=(503,)),
    )
    def get(self, request):
        client = GitHubOAuthClient()
        redirect_path = safe_redirect_path(request.query_params.get("redirect", ""))
        state = social_login_service.build_state(redirect=redirect_path)
        return Response({"authorize_url": client.authorize_url(state=state)})


class GitHubLoginCallbackView(APIView):
    """GitHub redirects the browser here after the user grants access."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(exclude=True)
    def get(self, request):
        frontend = settings.FRONTEND_SITE_URL.rstrip("/")
        try:
            payload = social_login_service.consume_state(
                request.query_params.get("state", "")
            )
            code = request.query_params.get("code", "")
            if not code:
                raise InvalidSocialState("GitHub did not return an authorization code.")
            profile = GitHubOAuthClient().fetch_profile(code=code)
            user = social_login_service.login(profile)
        except ApplicationError as exc:
            logger.info("Social sign-in rejected", extra={"code": exc.code})
            return HttpResponseRedirect(f"{frontend}/login")
        tokens = TokenService.create_tokens(user)
        response = HttpResponseRedirect(
            f"{frontend}{safe_redirect_path(str(payload.get('redirect') or '/'))}"
        )
        TokenService.set_refresh_cookie(response, tokens["refresh"])
        return response
