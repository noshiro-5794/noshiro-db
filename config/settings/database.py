import dj_database_url

from .base import DEBUG

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        conn_max_age=0 if DEBUG else 60,
        conn_health_checks=True,
        ssl_require=not DEBUG,
    )
}
