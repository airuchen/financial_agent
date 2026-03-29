from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Literal, TypeVar

T = TypeVar("T")

ServiceName = Literal["search", "llm"]
FailureKind = Literal["timeout", "rate_limit", "backend", "provider"]


class ExternalServiceError(Exception):
    """Typed failure surfaced to the API layer."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers


class SearchTimeoutError(ExternalServiceError):
    def __init__(self, message: str = "Search request timed out.") -> None:
        super().__init__(504, "search_timeout", message)


class SearchRateLimitError(ExternalServiceError):
    def __init__(
        self,
        message: str = "Search provider rate limited the request. Please retry later.",
    ) -> None:
        super().__init__(429, "search_rate_limited", message, {"Retry-After": "30"})


class SearchBackendError(ExternalServiceError):
    def __init__(
        self,
        message: str = "Search backend unavailable. Please retry later.",
    ) -> None:
        super().__init__(503, "search_backend_unavailable", message)


class SearchProviderError(ExternalServiceError):
    def __init__(
        self,
        message: str = "Search provider failed to process the request.",
    ) -> None:
        super().__init__(503, "search_provider_failure", message)


class LLMTimeoutError(ExternalServiceError):
    def __init__(self, message: str = "LLM request timed out.") -> None:
        super().__init__(504, "llm_timeout", message)


class LLMRateLimitError(ExternalServiceError):
    def __init__(
        self,
        message: str = "LLM provider rate limited the request. Please retry later.",
    ) -> None:
        super().__init__(429, "llm_rate_limited", message, {"Retry-After": "30"})


class LLMBackendError(ExternalServiceError):
    def __init__(
        self,
        message: str = "LLM backend unavailable. Please retry later.",
    ) -> None:
        super().__init__(503, "llm_backend_unavailable", message)


class LLMProviderError(ExternalServiceError):
    def __init__(
        self,
        message: str = "LLM provider failed to process the request.",
    ) -> None:
        super().__init__(503, "llm_provider_failure", message)


def map_external_error(
    exc: BaseException, *, service: ServiceName
) -> ExternalServiceError:
    """Convert a provider/search failure into a typed API error."""
    if isinstance(exc, ExternalServiceError):
        return exc

    kind = _classify_failure_kind(exc)
    if service == "search":
        if kind == "timeout":
            return SearchTimeoutError()
        if kind == "rate_limit":
            return SearchRateLimitError()
        if kind == "backend":
            return SearchBackendError()
        return SearchProviderError()

    if kind == "timeout":
        return LLMTimeoutError()
    if kind == "rate_limit":
        return LLMRateLimitError()
    if kind == "backend":
        return LLMBackendError()
    return LLMProviderError()


async def retry_async[T](
    operation: Callable[[], Awaitable[T]],
    *,
    service: ServiceName,
    max_attempts: int = 3,
    initial_delay: float = 0.2,
    max_delay: float = 1.0,
) -> T:
    """Retry transient provider/search failures with bounded exponential backoff."""
    delay = initial_delay
    last_error: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            last_error = exc
            mapped = map_external_error(exc, service=service)
            if not _is_retryable(mapped) or attempt >= max_attempts:
                raise mapped from exc
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

    assert last_error is not None
    raise map_external_error(last_error, service=service) from last_error


def empty_search_response() -> str:
    return (
        "I couldn't find any current web results for this question, so I can't "
        "confirm an answer from live sources right now."
    )


def _is_retryable(error: ExternalServiceError) -> bool:
    return isinstance(
        error,
        (
            SearchTimeoutError,
            SearchRateLimitError,
            SearchBackendError,
            LLMTimeoutError,
            LLMRateLimitError,
            LLMBackendError,
        ),
    )


def _classify_failure_kind(exc: BaseException) -> FailureKind:
    text = f"{type(exc).__name__}: {exc}".lower()
    if _looks_like_timeout(text):
        return "timeout"
    if _looks_like_rate_limit(text):
        return "rate_limit"
    if _looks_like_backend(text):
        return "backend"
    return "provider"


def _looks_like_timeout(text: str) -> bool:
    return bool(
        re.search(
            (
                r"timeout|timed out|readtimeout|connecttimeout|sockettimeout|"
                r"deadline exceeded"
            ),
            text,
        )
    )


def _looks_like_rate_limit(text: str) -> bool:
    return bool(
        re.search(
            r"rate limit|too many requests|429|quota exceeded|throttl",
            text,
        )
    )


def _looks_like_backend(text: str) -> bool:
    return bool(
        re.search(
            (
                r"unavailable|service unavailable|bad gateway|gateway timeout|"
                r"connection|network|backend|server error|502|503|504"
            ),
            text,
        )
    )
