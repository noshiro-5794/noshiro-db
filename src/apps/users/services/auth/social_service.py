"""Third-party sign-in, currently GitHub.

The flow is a plain server-side OAuth 2.0 authorization-code exchange: the SPA
asks for an authorize URL, GitHub redirects the browser back to this API, and
the API answers with the same HttpOnly refresh cookie the password login sets.
Tokens therefore never touch JavaScript or the URL bar.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass

import httpx
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db import transaction

from apps.users.exceptions import (
    InvalidSocialState,
    SocialEmailMissing,
    SocialLoginUnavailable,
    SocialProviderError,
)
from apps.users.models import SocialIdentity, User, UserProfile
from shared.outbound import proxy_for_url

logger = logging.getLogger(__name__)

STATE_SALT = "users.social-login.state"
NONCE_CACHE_PREFIX = "users:social-login:nonce:"
NICKNAME_MAX_LENGTH = 200


@dataclass(frozen=True)
class SocialProfile:
    provider: str
    subject: str
    email: str
    email_verified: bool
    handle: str
    display_name: str
    avatar_url: str


class GitHubOAuthClient:
    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_URL = "https://api.github.com/user"
    EMAILS_URL = "https://api.github.com/user/emails"

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        scopes: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.client_id = (
            client_id if client_id is not None else settings.GITHUB_OAUTH_CLIENT_ID
        )
        self.client_secret = (
            client_secret
            if client_secret is not None
            else settings.GITHUB_OAUTH_CLIENT_SECRET
        )
        self.redirect_uri = (
            redirect_uri
            if redirect_uri is not None
            else settings.GITHUB_OAUTH_REDIRECT_URI
        )
        self.scopes = scopes if scopes is not None else settings.GITHUB_OAUTH_SCOPES
        self.timeout = timeout if timeout is not None else settings.GITHUB_OAUTH_TIMEOUT

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def authorize_url(self, *, state: str) -> str:
        if not self.is_configured:
            raise SocialLoginUnavailable()
        query = httpx.QueryParams(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": self.scopes,
                "state": state,
                "allow_signup": "true",
            }
        )
        return f"{self.AUTHORIZE_URL}?{query}"

    def fetch_profile(self, *, code: str) -> SocialProfile:
        token = self._exchange_code(code)
        payload = self._get_json(self.USER_URL, token)
        subject = payload.get("id")
        if subject is None:
            raise SocialProviderError("GitHub did not return an account id.")
        email = self._verified_email(token, payload)
        return SocialProfile(
            provider=SocialIdentity.Provider.GITHUB,
            subject=str(subject),
            email=email,
            email_verified=True,
            handle=str(payload.get("login") or "")[:191],
            display_name=str(payload.get("name") or payload.get("login") or "")[:256],
            avatar_url=str(payload.get("avatar_url") or "")[:1024],
        )

    def _exchange_code(self, code: str) -> str:
        if not self.is_configured:
            raise SocialLoginUnavailable()
        try:
            response = httpx.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
                timeout=self.timeout,
                proxy=proxy_for_url(self.TOKEN_URL),
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("GitHub token exchange failed", exc_info=True)
            raise SocialProviderError() from exc
        token = data.get("access_token") if isinstance(data, dict) else None
        if not token:
            raise SocialProviderError("GitHub rejected the authorization code.")
        return str(token)

    def _get_json(self, url: str, token: str) -> dict:
        try:
            response = httpx.get(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=self.timeout,
                proxy=proxy_for_url(url),
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("GitHub profile request failed", exc_info=True)
            raise SocialProviderError() from exc
        if not isinstance(data, dict):
            raise SocialProviderError("GitHub returned an unexpected payload.")
        return data

    def _verified_email(self, token: str, profile: dict) -> str:
        public_email = profile.get("email")
        if isinstance(public_email, str) and public_email:
            return User.objects.normalize_email(public_email)
        try:
            emails = httpx.get(
                self.EMAILS_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=self.timeout,
                proxy=proxy_for_url(self.EMAILS_URL),
            )
            emails.raise_for_status()
            rows = emails.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("GitHub email request failed", exc_info=True)
            raise SocialProviderError() from exc
        for row in rows if isinstance(rows, list) else []:
            if (
                isinstance(row, dict)
                and row.get("verified")
                and isinstance(row.get("email"), str)
            ):
                return User.objects.normalize_email(row["email"])
        raise SocialEmailMissing()


class SocialLoginService:
    """Verify the OAuth state and resolve it to a local account."""

    @staticmethod
    def build_state(*, redirect: str) -> str:
        """Sign a single-use state token that also carries the return path."""
        nonce = secrets.token_urlsafe(24)
        ttl = settings.GITHUB_OAUTH_STATE_TTL
        cache.set(f"{NONCE_CACHE_PREFIX}{nonce}", "1", timeout=ttl)
        return signing.dumps(
            {"nonce": nonce, "redirect": redirect},
            salt=STATE_SALT,
            compress=True,
        )

    @staticmethod
    def consume_state(state: str) -> dict:
        """Return the signed payload once, rejecting replays and stale links."""
        if not state:
            raise InvalidSocialState()
        try:
            payload = signing.loads(
                state,
                salt=STATE_SALT,
                max_age=settings.GITHUB_OAUTH_STATE_TTL,
            )
        except signing.BadSignature as exc:
            raise InvalidSocialState() from exc
        nonce = payload.get("nonce") if isinstance(payload, dict) else None
        if not nonce or not cache.delete(f"{NONCE_CACHE_PREFIX}{nonce}"):
            raise InvalidSocialState()
        return payload

    @classmethod
    @transaction.atomic
    def login(cls, profile: SocialProfile) -> User:
        identity = (
            SocialIdentity.objects.select_related("user")
            .filter(provider=profile.provider, subject=profile.subject)
            .first()
        )
        if identity is not None:
            cls._refresh_identity(identity, profile)
            return identity.user
        user = User.objects.filter(email__iexact=profile.email).first()
        if user is None:
            user = cls._create_user(profile)
        SocialIdentity.objects.create(
            user=user,
            provider=profile.provider,
            subject=profile.subject,
            handle=profile.handle,
            email=profile.email,
            avatar_url=profile.avatar_url,
        )
        return user

    @staticmethod
    def _refresh_identity(identity: SocialIdentity, profile: SocialProfile) -> None:
        updates = {}
        if profile.handle and profile.handle != identity.handle:
            updates["handle"] = profile.handle
        if profile.avatar_url and profile.avatar_url != identity.avatar_url:
            updates["avatar_url"] = profile.avatar_url
        if profile.email and profile.email != identity.email:
            updates["email"] = profile.email
        if updates:
            SocialIdentity.objects.filter(pk=identity.pk).update(**updates)

    @classmethod
    def _create_user(cls, profile: SocialProfile) -> User:
        user = User.objects.create_user(email=profile.email, password=None)
        user.is_email_verified = profile.email_verified
        user.save(update_fields=["is_email_verified"])
        UserProfile.objects.create(
            user=user,
            nickname=cls._unique_nickname(profile.display_name or profile.handle),
            avatar=profile.avatar_url,
        )
        return user

    @staticmethod
    def _unique_nickname(base: str) -> str:
        candidate = (base or "user").strip()[:NICKNAME_MAX_LENGTH] or "user"
        suffix = 1
        while UserProfile.objects.filter(nickname=candidate).exists():
            suffix += 1
            tail = f"-{suffix}"
            candidate = f"{candidate[: NICKNAME_MAX_LENGTH - len(tail)]}{tail}"
        return candidate


github_oauth_client = GitHubOAuthClient()
social_login_service = SocialLoginService()


__all__ = [
    "GitHubOAuthClient",
    "SocialLoginService",
    "SocialProfile",
    "github_oauth_client",
    "social_login_service",
]
