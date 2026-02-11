from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    source: str
    credibility: str
    content: str
    metadata: dict[str, Any]


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


class ResearchCorpus:
    """独立资料库，模拟 WebSearch + 来源可信度评估."""

    def __init__(self, data_path: str | Path):
        raw = json.loads(Path(data_path).read_text(encoding="utf-8"))
        self.sources = [Source(**item) for item in raw]

    def search(self, query: str, limit: int = 5) -> list[Source]:
        query_terms = tokenize(query)
        ranked = []
        for source in self.sources:
            source_terms = tokenize(source.title + " " + source.content + " " + " ".join(map(str, source.metadata.values())))
            overlap = len(query_terms & source_terms)
            credibility_boost = {"high": 3, "medium": 1, "low": 0}.get(source.credibility, 0)
            score = overlap + credibility_boost
            if score > 0:
                ranked.append((score, source))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [source for _, source in ranked[:limit]]


def citation(source: Source, index: int) -> dict[str, Any]:
    return {
        "index": index,
        "title": source.title,
        "source": source.source,
        "credibility": source.credibility,
        "snippet": source.content[:220],
    }
