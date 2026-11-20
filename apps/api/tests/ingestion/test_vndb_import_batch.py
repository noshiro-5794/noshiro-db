import json

import httpx
import pytest

from api.integrations.providers.errors import ProviderError
from api.integrations.providers.vndb import VN_FIELDS, VNDBClient


def test_import_batch_fetches_paginated_relations_and_deduplicated_staff():
    requests = []
    work = {
        "id": "v1",
        "staff": [{"id": "s12"}, {"id": 12}, {"id": "invalid"}, {"id": True}],
        "va": [{"staff": {"id": "s13"}}, {"staff": {"id": "s12"}}],
    }

    def handler(request):
        body = json.loads(request.content)
        endpoint = request.url.path
        requests.append((endpoint, body))
        if endpoint == "/vn":
            return httpx.Response(200, json={"results": [work]})
        if endpoint == "/staff":
            return httpx.Response(200, json={"results": [{"id": body["filters"][2][2]}]})
        if endpoint == "/release":
            page = body["page"]
            return httpx.Response(200, json={"results": [{"id": f"r{page}"}], "more": page == 1})
        return httpx.Response(200, json={"results": [], "more": False})

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://provider.test"
    ) as http:
        batch = VNDBClient(http=http).fetch_import_batch("v1")

    assert batch.work == work
    assert batch.related_fetched
    assert batch.releases == ({"id": "r1"}, {"id": "r2"})
    assert batch.characters == ()
    assert batch.contributors == ({"id": "s12"}, {"id": "s13"})
    assert requests[0][1]["fields"] == VN_FIELDS
    assert [body["filters"] for path, body in requests if path == "/staff"] == [
        ["and", ["ismain", "=", 1], ["id", "=", "s12"]],
        ["and", ["ismain", "=", 1], ["id", "=", "s13"]],
    ]
    assert all(
        body["filters"] == ["vn", "=", ["id", "=", "v1"]]
        for path, body in requests
        if path in {"/release", "/character"}
    )


def test_import_batch_can_fetch_only_the_work():
    requests = []

    def handler(request):
        requests.append(request.url.path)
        return httpx.Response(200, json={"results": [{"id": "v1", "staff": [{"id": 12}]}]})

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://provider.test"
    ) as http:
        batch = VNDBClient(http=http).fetch_import_batch("v1", include_related=False)
    assert not batch.related_fetched
    assert batch.releases == batch.characters == batch.contributors == ()
    assert requests == ["/vn"]


def test_import_batch_preserves_missing_work_error():
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"results": []})
            ),
            base_url="https://provider.test",
        ) as http,
        pytest.raises(ProviderError) as failure,
    ):
        VNDBClient(http=http).fetch_import_batch("v404")
    assert failure.value.status_code == 404
