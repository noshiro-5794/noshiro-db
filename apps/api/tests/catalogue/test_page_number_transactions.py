import pytest

from api.contexts.library.tags import create_tag
from api.db import fetch
from api.worker import mal_import
from tests.catalogue.test_cursor_transactions import cursor_client as cursor_client


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["tags", "catalogue"])
async def test_last_page_selects_the_final_database_window_and_preserves_links(
    cursor_client, register_provider, kind
):
    session, user_id, client = cursor_client
    await register_provider("mal", "MyAnimeList")
    for index in range(5):
        await create_tag(session, user_id=user_id, name=f"tag-{index}")
        await mal_import.import_anime(session, {"id": index + 1, "title": f"Anime {index}"})
    paths = {
        "tags": "/api/v1/users/me/tags/",
        "catalogue": "/api/v1/index/entities/?scope=all",
    }
    orders = {
        "tags": "user_tag ORDER BY name,id",
        "catalogue": "entity ORDER BY updated_at DESC,id",
    }
    expected = [str(row.id) for row in await fetch(session, "SELECT id FROM " + orders[kind], {})]
    path = paths[kind] + ("&" if "?" in paths[kind] else "?") + "page=last&page_size=2"
    response = await client.get(path)
    assert response.status_code == 200, response.text
    last = response.json()
    assert last["count"] == 5 and last["next"] is None
    assert [str(row["id"]) for row in last["results"]] == expected[4:]
    previous = (await client.get(last["previous"])).json()
    assert [str(row["id"]) for row in previous["results"]] == expected[2:4]
    first = (await client.get(previous["previous"])).json()
    assert [str(row["id"]) for row in first["results"]] == expected[:2]
    assert first["previous"] is None
    for value in ["0", "-1", "invalid", str(2**80)]:
        invalid = await client.get(path.replace("page=last", "page=" + value))
        assert invalid.status_code == 404 and invalid.json()["detail"] == "Invalid page."
