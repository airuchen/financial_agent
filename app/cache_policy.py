import hashlib
from dataclasses import dataclass
from typing import Literal

from app.cache import normalize_query

CacheClass = Literal["critical_market", "direct_knowledge", "search_noncritical"]


@dataclass(frozen=True)
class CacheKeyContext:
    model: str
    prompt_revision: str


def classify_cache_policy(query: str) -> CacheClass:
    """Classify query by freshness requirements for cache usage."""
    q = normalize_query(query)

    critical_keywords = (
        "current",
        "latest",
        "live",
        "now",
        "today",
        "spot",
        "intraday",
        "real-time",
        "real time",
        "quote",
        "price",
        "eur/usd",
        "usd/eur",
        "fx rate",
        "exchange rate",
        "stock price",
    )
    if any(k in q for k in critical_keywords):
        return "critical_market"

    direct_prefixes = (
        "what is ",
        "explain ",
        "define ",
        "how does ",
        "hello",
        "hi",
        "hey",
    )
    if q.startswith(direct_prefixes):
        return "direct_knowledge"

    noncritical_keywords = (
        "summarize",
        "summary",
        "regulatory",
        "regulation",
        "earnings call",
        "last week",
        "this week",
        "yesterday",
        "minutes",
        "filing",
    )
    if any(k in q for k in noncritical_keywords):
        return "search_noncritical"

    # Strict accuracy default: uncertain queries are treated as critical.
    return "critical_market"


def query_hash(query: str) -> str:
    normalized = normalize_query(query)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def direct_answer_cache_key(query: str, ctx: CacheKeyContext) -> str:
    return (
        f"agent:direct:v1:{query_hash(query)}:{ctx.model}:{ctx.prompt_revision}"
    )


def search_answer_cache_key(query: str, ctx: CacheKeyContext) -> str:
    return (
        f"agent:search_answer:v1:{query_hash(query)}:{ctx.model}:{ctx.prompt_revision}"
    )


def search_results_cache_key(query: str) -> str:
    return f"agent:search_results:v1:{query_hash(query)}"
