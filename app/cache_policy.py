import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from app.cache import normalize_query

CacheClass = Literal["critical_market", "direct_knowledge", "search_noncritical"]


@dataclass(frozen=True)
class CacheKeyContext:
    model: str
    prompt_revision: str


def has_time_critical_finance_signal(query: str) -> bool:
    """Detect clearly time-sensitive finance queries that must route to search."""
    q = normalize_query(query)
    critical_signals = (
        "current",
        "latest",
        "live",
        "now",
        "today",
        "spot",
        "intraday",
        "real-time",
        "real time",
        "price",
        "quote",
        "stock",
        "fx rate",
        "eur/usd",
        "usd/eur",
        "exchange rate",
        "fed decision",
        "market open",
    )
    return any(signal in q for signal in critical_signals)


def is_casual_query(query: str) -> bool:
    """Detect greeting/small-talk queries that should never trigger web search."""
    q = normalize_query(query)
    if has_time_critical_finance_signal(q):
        return False

    casual_patterns = (
        r"^(hello|hi|hey|yo|hiya|greetings)[!.?]*$",
        r"^(hello|hi|hey)\s+(there|team|bot)[!.?]*$",
        r"^how are (you|u)[?.!]*$",
        r"^what('?s|\s+is)\s+up[?.!]*$",
        r"^good\s+(morning|afternoon|evening)[!.?]*$",
        r"^nice to meet you[!.?]*$",
    )
    return any(re.match(pattern, q) for pattern in casual_patterns)


def classify_cache_policy(query: str) -> CacheClass:
    """Classify query by freshness requirements for cache usage."""
    q = normalize_query(query)

    if has_time_critical_finance_signal(q):
        return "critical_market"

    if is_casual_query(q):
        return "direct_knowledge"

    direct_prefixes = (
        "what is ",
        "explain ",
        "define ",
        "how does ",
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
    return f"agent:direct:v1:{query_hash(query)}:{ctx.model}:{ctx.prompt_revision}"


def search_answer_cache_key(query: str, ctx: CacheKeyContext) -> str:
    return (
        f"agent:search_answer:v1:{query_hash(query)}:{ctx.model}:{ctx.prompt_revision}"
    )


def search_results_cache_key(query: str) -> str:
    return f"agent:search_results:v1:{query_hash(query)}"
