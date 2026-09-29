from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.users.api.views.social import safe_redirect_path
from apps.users.exceptions import InvalidSocialState
from apps.users.models import SocialIdentity, User, UserProfile
from apps.users.services.auth.social_service import (
    SocialLoginService,
    SocialProfile,
    social_login_service,
)

pytestmark = pytest.mark.django_db

CONFIGURED = override_settings(
    GITHUB_OAUTH_CLIENT_ID="client-id",
    GITHUB_OAUTH_CLIENT_SECRET="client-secret",
    GITHUB_OAUTH_REDIRECT_URI="https://api.example.test/api/v1/auth/social/github/callback/",
    FRONTEND_SITE_URL="https://app.example.test",
    JWT_REFRESH_COOKIE_DOMAIN=None,
)


def _profile(**overrides) -> SocialProfile:
    values = {
        "provider": SocialIdentity.Provider.GITHUB,
        "subject": "4242",
        "email": "octocat@example.com",
        "email_verified": True,
        "handle": "octocat",
        "display_name": "The Octocat",
        "avatar_url": "https://avatars.example.test/u/4242",
    }
    values.update(overrides)
    return SocialProfile(**values)


def test_only_relative_return_paths_are_accepted() -> None:
    assert safe_redirect_path("/library") == "/library"
    assert safe_redirect_path("") == "/"
    assert safe_redirect_path("https://evil.test") == "/"
    assert safe_redirect_path("//evil.test") == "/"


@CONFIGURED
def test_start_endpoint_returns_the_provider_authorize_url() -> None:
    response = APIClient().get(
        "/api/v1/auth/social/github/start/", {"redirect": "/library"}
    )

    assert response.status_code == 200
    url = response.json()["authorize_url"]
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=client-id" in url
    assert "state=" in url


@override_settings(GITHUB_OAUTH_CLIENT_ID="", GITHUB_OAUTH_CLIENT_SECRET="")
def test_start_endpoint_is_unavailable_without_credentials() -> None:
    response = APIClient().get("/api/v1/auth/social/github/start/")

    assert response.status_code == 503


@override_settings(GITHUB_OAUTH_CLIENT_ID="", GITHUB_OAUTH_CLIENT_SECRET="")
def test_provider_list_reports_whether_github_is_enabled() -> None:
    response = APIClient().get("/api/v1/auth/social/providers/")

    assert response.status_code == 200
    assert response.json() == [
        {
            "provider": "github",
            "enabled": False,
            "authorize_path": "/api/v1/auth/social/github/start/",
        }
    ]


@CONFIGURED
def test_callback_rejects_a_forged_state() -> None:
    response = APIClient().get(
        "/api/v1/auth/social/github/callback/",
        {"code": "abc", "state": "not-a-real-state"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "https://app.example.test/login"
    assert User.objects.count() == 0


def test_state_tokens_are_single_use() -> None:
    state = social_login_service.build_state(redirect="/library")

    assert SocialLoginService.consume_state(state)["redirect"] == "/library"
    with pytest.raises(InvalidSocialState):
        SocialLoginService.consume_state(state)


@CONFIGURED
def test_callback_creates_an_account_and_sets_the_refresh_cookie() -> None:
    state = social_login_service.build_state(redirect="/library")
    with patch(
        "apps.users.api.views.social.GitHubOAuthClient.fetch_profile",
        return_value=_profile(),
    ):
        response = APIClient().get(
            "/api/v1/auth/social/github/callback/",
            {"code": "abc", "state": state},
        )

    assert response.status_code == 302
    assert response.headers["Location"] == "https://app.example.test/library"
    assert "noshiro_refresh" in response.cookies
    user = User.objects.get(email="octocat@example.com")
    assert user.is_email_verified is True
    assert user.has_usable_password() is False
    assert user.profile.nickname == "The Octocat"
    assert SocialIdentity.objects.filter(user=user, subject="4242").exists()


@CONFIGURED
def test_callback_links_to_an_existing_password_account() -> None:
    existing = User.objects.create_user(
        email="octocat@example.com", password="s3cret-pass"
    )
    UserProfile.objects.create(user=existing, nickname="octocat")
    state = social_login_service.build_state(redirect="/")

    with patch(
        "apps.users.api.views.social.GitHubOAuthClient.fetch_profile",
        return_value=_profile(),
    ):
        APIClient().get(
            "/api/v1/auth/social/github/callback/",
            {"code": "abc", "state": state},
        )

    assert User.objects.count() == 1
    assert SocialIdentity.objects.get(user=existing).subject == "4242"


def test_duplicate_nicknames_are_suffixed() -> None:
    existing = User.objects.create_user(email="first@example.com")
    UserProfile.objects.create(user=existing, nickname="octocat")

    user = SocialLoginService._create_user(
        _profile(subject="99", display_name="octocat", email="second@example.com")
    )

    assert user.profile.nickname == "octocat-2"
