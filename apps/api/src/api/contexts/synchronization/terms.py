"""Normalize textual alias lookup keys."""

import re
import unicodedata


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip().lower())
