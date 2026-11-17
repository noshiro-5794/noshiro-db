"""S3-compatible object uploads with existing deployment setting aliases."""

from typing import TYPE_CHECKING
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    endpoint: str = Field(
        default="", validation_alias=AliasChoices("S3_ENDPOINT_URL", "MINIO_ENDPOINT")
    )
    access_key: str = Field(
        default="", validation_alias=AliasChoices("S3_ACCESS_KEY", "MINIO_ACCESS_KEY")
    )
    secret_key: str = Field(
        default="", validation_alias=AliasChoices("S3_SECRET_KEY", "MINIO_SECRET_KEY")
    )
    bucket: str = Field(default="", validation_alias=AliasChoices("S3_BUCKET", "MINIO_BUCKET"))
    public_url: str = Field(
        default="", validation_alias=AliasChoices("S3_PUBLIC_URL", "MINIO_PUBLIC_URL")
    )
    use_https: bool = Field(default=False, validation_alias="MINIO_USE_HTTPS")

    @property
    def endpoint_url(self) -> str:
        endpoint = self.endpoint.strip().rstrip("/")
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        scheme = "https" if self.use_https else "http"
        return f"{scheme}://{endpoint}"


class ObjectStorage:
    def __init__(self, settings: StorageSettings | None = None) -> None:
        self.settings = settings or StorageSettings()
        self._client: S3Client | None = None
        self._bucket_ready = False

    @property
    def client(self) -> "S3Client":
        if self._client is None:
            settings = self.settings
            if not all(
                (settings.endpoint, settings.access_key, settings.secret_key, settings.bucket)
            ):
                raise ValueError("Object storage endpoint, credentials and bucket are required.")
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.endpoint_url,
                aws_access_key_id=settings.access_key,
                aws_secret_access_key=settings.secret_key,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        return self._client

    def upload_bytes(self, name: str, data: bytes, content_type: str) -> str:
        name = name.strip().replace("\\", "/").strip("/")
        if not name or any(part in {"", ".", ".."} for part in name.split("/")):
            raise ValueError("Object name must be a non-empty relative path.")
        client = self.client
        bucket = self.settings.bucket
        if not self._bucket_ready:
            try:
                client.head_bucket(Bucket=bucket)
            except ClientError as error:
                if error.response["Error"].get("Code") not in {"404", "NoSuchBucket", "NotFound"}:
                    raise
                try:
                    client.create_bucket(Bucket=bucket)
                except ClientError as creation_error:
                    if creation_error.response["Error"].get("Code") not in {
                        "BucketAlreadyExists",
                        "BucketAlreadyOwnedByYou",
                    }:
                        raise
            self._bucket_ready = True
        client.put_object(Bucket=bucket, Key=name, Body=data, ContentType=content_type)
        base = (self.settings.public_url or self.settings.endpoint_url).rstrip("/")
        return f"{base}/{quote(bucket)}/{quote(name, safe='/')}"

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._bucket_ready = False
