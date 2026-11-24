from types import SimpleNamespace

import pytest

from api.contexts.presentation.summary import choose_name


@pytest.mark.parametrize("native_language", ["ja", ""])
def test_japanese_title_prefers_native_script_when_romaji_is_official(native_language):
    names = [
        SimpleNamespace(
            id=1,
            text="Sousou no Frieren",
            language="ja",
            kind="romanized",
            is_official=True,
            is_original=False,
        ),
        SimpleNamespace(
            id=2,
            text="葬送のフリーレン",
            language=native_language,
            kind="original",
            is_official=False,
            is_original=True,
        ),
        SimpleNamespace(
            id=3,
            text="Frieren: Beyond Journey's End",
            language="en",
            kind="official",
            is_official=True,
            is_original=False,
        ),
    ]
    assert choose_name(names, "ja-JP") == "葬送のフリーレン"
    assert choose_name(names, "en-US") == "Frieren: Beyond Journey's End"
