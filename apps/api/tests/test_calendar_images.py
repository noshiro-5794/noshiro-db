from unittest.mock import Mock

import httpx
import pytest

from api.integrations.storage import ObjectStorage
from api.worker.calendar_images import CalendarImages, allowed_url


@pytest.mark.parametrize("url", ["https://evil.test/a.jpg", "file:///a.jpg", "http://[bad"])
def test_image_allowlist_rejects_unusable_urls(url):
    assert not allowed_url(url)


def test_image_size_and_content_type_are_checked_before_upload(monkeypatch):
    monkeypatch.setenv("BANGUMI_IMAGE_MAX_BYTES", "3")
    storage = Mock(spec=ObjectStorage)
    payloads = [
        ({"content-type": "text/html"}, b"a"),
        ({"content-type": "image/png", "content-length": "4"}, b"abcd"),
        ({"content-type": "image/png"}, b"abcd"),
        ({"content-type": "image/png"}, b"abc"),
    ]
    for headers, data in payloads:
        http = httpx.Client(
            transport=httpx.MockTransport(
                lambda request, headers=headers, data=data: httpx.Response(
                    200, headers=headers, content=data
                )
            )
        )
        images = CalendarImages(http=http, storage=storage)
        images.cache_cover(1, {"large": "https://lain.bgm.tv/cover.jpg"})
        images.close()
        assert http.is_closed
    storage.upload_bytes.assert_called_once_with("calendar-covers/1.png", b"abc", "image/png")
    assert storage.close.call_count == 4


def test_upload_failure_keeps_calendar_processing_available():
    storage = Mock(spec=ObjectStorage)
    storage.upload_bytes.side_effect = ValueError("storage unavailable")
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, headers={"content-type": "image/webp"}, content=b"image"
            )
        )
    )
    images = CalendarImages(http=http, storage=storage)
    try:
        assert images.cache_cover(1, {"common": "https://lain.bgm.tv/cover"}) == ""
    finally:
        images.close()
    storage.upload_bytes.assert_called_once_with("calendar-covers/1.webp", b"image", "image/webp")
