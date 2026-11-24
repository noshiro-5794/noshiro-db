"""Conservative language hints for source titles without a locale tag."""

import re


def title_language(text: str) -> str:
    if re.search(r"[\u3041-\u3096\u30a1-\u30fa]", text):
        return "ja"
    if re.search(r"[\uac00-\ud7a3]", text):
        return "ko"
    return "und"
