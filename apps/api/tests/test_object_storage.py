import pytest
from botocore.stub import Stubber

from api.integrations.storage import ObjectStorage, StorageSettings


@pytest.fixture
def storage():
    storage = ObjectStorage(
        StorageSettings(
            _env_file=None,
            S3_ENDPOINT_URL="http://storage.test:9000",
            S3_ACCESS_KEY="fixture",
            S3_SECRET_KEY="fixture",
            S3_BUCKET="catalogue",
            S3_PUBLIC_URL="https://media.test",
        )
    )
    try:
        yield storage
    finally:
        storage.close()


def test_upload_uses_existing_bucket_and_encodes_public_url(storage):
    with Stubber(storage.client) as stub:
        stub.add_response("head_bucket", {}, {"Bucket": "catalogue"})
        for _ in range(2):
            stub.add_response(
                "put_object",
                {},
                {
                    "Bucket": "catalogue",
                    "Key": "calendar-covers/a b.png",
                    "Body": b"image",
                    "ContentType": "image/png",
                },
            )
        for _ in range(2):
            assert storage.upload_bytes("calendar-covers/a b.png", b"image", "image/png") == (
                "https://media.test/catalogue/calendar-covers/a%20b.png"
            )
        stub.assert_no_pending_responses()


def test_missing_bucket_creation_tolerates_concurrent_creator(storage):
    with Stubber(storage.client) as stub:
        stub.add_client_error("head_bucket", "404", http_status_code=404)
        stub.add_client_error("create_bucket", "BucketAlreadyOwnedByYou", http_status_code=409)
        stub.add_response("put_object", {})
        storage.upload_bytes("cover.png", b"image", "image/png")
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("name", ["", "../file", "a/../file", "a//b", "./file"])
def test_invalid_object_paths_fail_before_initializing_client(storage, name):
    with pytest.raises(ValueError, match="relative path"):
        storage.upload_bytes(name, b"image", "image/png")
    assert storage._client is None


def test_legacy_settings_keep_endpoint_scheme_and_public_url_fallback():
    settings = StorageSettings(
        _env_file=None,
        MINIO_ENDPOINT="https://storage.test:9000/",
        MINIO_ACCESS_KEY="fixture",
        MINIO_SECRET_KEY="fixture",
        MINIO_BUCKET="catalogue",
    )
    assert settings.endpoint_url == "https://storage.test:9000"


def test_s3_setting_names_take_precedence_over_legacy_aliases():
    settings = StorageSettings(
        _env_file=None,
        S3_ENDPOINT_URL="https://new.test",
        MINIO_ENDPOINT="old.test",
    )
    assert settings.endpoint_url == "https://new.test"
