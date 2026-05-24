from .common import *

DEBUG = False

if not SECRET_KEY or SECRET_KEY == "unsafe-secret-key":
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")

if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set in production.")

if CORS_ALLOW_ALL_ORIGINS:
    raise RuntimeError("CORS_ALLOW_ALL_ORIGINS must be False in production.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_SECURE = True

CSRF_COOKIE_HTTPONLY = False

SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30

SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_HSTS_PRELOAD = True
