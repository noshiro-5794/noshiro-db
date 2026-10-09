from typing import Any

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    @classmethod
    def normalize_email(cls, email: str) -> str:
        return super().normalize_email(email).casefold()

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        if not email:
            raise ValueError("The email field must be set.")

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "user"

    def __str__(self) -> str:
        return self.email


class SocialIdentity(models.Model):
    """Link between a local account and an external sign-in provider.

    Kept separate from the user row so someone who registered with a password
    can attach GitHub later, and so one account can carry several providers
    without the user table growing a column per provider.
    """

    class Provider(models.TextChoices):
        GITHUB = "github", "GitHub"

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="social_identities",
    )
    provider = models.CharField(max_length=32, choices=Provider.choices)
    # The provider's own stable user id, never the handle: handles are renameable.
    subject = models.CharField(max_length=191)
    handle = models.CharField(max_length=191, blank=True)
    email = models.EmailField(blank=True)
    avatar_url = models.URLField(max_length=1024, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "social_identity"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "subject"],
                name="uq_social_identity_subject",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "provider"],
                name="idx_social_identity_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.handle or self.subject}"


class EmailVerification(models.Model):
    class Purpose(models.TextChoices):
        REGISTER = "register", "Register"
        LOGIN = "login", "Login"
        RESET_PASSWORD = "reset_password", "Reset Password"

    email = models.EmailField()
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=16, choices=Purpose.choices)
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    expire_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "email_verification"
        indexes = [
            models.Index(
                fields=["email", "purpose", "-created_at"],
                name="idx_ev_email_purpose",
            ),
            models.Index(fields=["expire_at"], name="idx_ev_expire_at"),
        ]
