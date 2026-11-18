"""Names supplied by a source, including language, script and editorial flags."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceName:
    text: str
    language: str
    kind: str
    is_original: bool = False
    is_official: bool = False
    script: str = ""
