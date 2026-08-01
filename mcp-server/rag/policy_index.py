"""
mcp-server/rag/policy_index.py

Indexing step for search_policy: chunk resources/company_policy.md and
load it into a KeywordStore.

Chunked by its "## " markdown sections rather than a fixed word count,
since each section in the policy is already one self-contained topic
(stock thresholds, who can change inventory, confirmation/elicitation
triggers, alternative-part rules, audit trail) -- splitting on headings
keeps each chunk semantically whole instead of cutting a rule in half.
"""

import re
from pathlib import Path

from .keyword_search import KeywordStore

_POLICY_PATH = Path(__file__).parent.parent / "resources" / "company_policy.md"


def _split_into_sections(markdown_text: str) -> list[dict]:
    """Split on '## ' headings. parts[0] is the '# Title' preamble
    before the first '##' and is dropped -- it's a heading, not content."""
    parts = re.split(r"(?m)^## ", markdown_text)
    sections = []
    for part in parts[1:]:
        lines = part.strip().splitlines()
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        sections.append({"title": title, "body": body})
    return sections


def build_policy_index() -> KeywordStore:
    store = KeywordStore()
    text = _POLICY_PATH.read_text(encoding="utf-8")

    for section in _split_into_sections(text):
        chunk_text = f"{section['title']}\n{section['body']}"
        store.upsert(text=chunk_text, metadata={"section": section["title"]})

    return store


# Built once at import time -- re-import this module (or call
# build_policy_index() again) if company_policy.md changes on disk.
policy_store = build_policy_index()
