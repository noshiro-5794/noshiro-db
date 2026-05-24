import os

CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "False") == "True"

CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "False") == "True"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
