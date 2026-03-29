from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.security import (
    AuthRateLimiter,
    extract_api_key_from_headers,
    hash_api_key,
    parse_api_key_hashes,
    seconds_until_next_hour,
    seconds_until_next_minute,
)


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.ops = []

    def incr(self, key: str):
        self.ops.append(("incr", key))
        return self

    def expire(self, key: str, seconds: int, nx: bool = False):
        self.ops.append(("expire", key, seconds, nx))
        return self

    async def execute(self):
        results = []
        for op in self.ops:
            if op[0] == "incr":
                key = op[1]
                self.redis.counts[key] = self.redis.counts.get(key, 0) + 1
                results.append(self.redis.counts[key])
            elif op[0] == "expire":
                _, key, seconds, nx = op
                if not nx or key not in self.redis.expiries:
                    self.redis.expiries[key] = seconds
                results.append(True)
        return results


class FakeRedis:
    def __init__(self):
        self.counts = {}
        self.expiries = {}

    def pipeline(self, transaction: bool = True):
        return FakePipeline(self)


def _build_request(headers: list[tuple[bytes, bytes]], ip: str = "1.2.3.4") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/query",
        "headers": headers,
        "client": (ip, 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_valid_api_key_is_accepted():
    api_key = "live-secret"
    guard = AuthRateLimiter(
        FakeRedis(),
        api_key_hashes={"client-a": hash_api_key(api_key)},
        minute_limit=60,
        hour_limit=600,
    )
    request = _build_request([(b"authorization", f"Bearer {api_key}".encode())])
    await guard.enforce(request)


@pytest.mark.asyncio
async def test_missing_api_key_rejected_with_401():
    guard = AuthRateLimiter(
        FakeRedis(),
        api_key_hashes={"client-a": hash_api_key("live-secret")},
        minute_limit=60,
        hour_limit=600,
    )
    request = _build_request([])
    with pytest.raises(HTTPException) as exc:
        await guard.enforce(request)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_threshold():
    api_key = "live-secret"
    guard = AuthRateLimiter(
        FakeRedis(),
        api_key_hashes={"client-a": hash_api_key(api_key)},
        minute_limit=1,
        hour_limit=100,
    )
    request = _build_request([(b"authorization", f"Bearer {api_key}".encode())])
    await guard.enforce(request)
    with pytest.raises(HTTPException) as exc:
        await guard.enforce(request)
    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"]


@pytest.mark.asyncio
async def test_invalid_key_uses_ip_fallback_rate_scope():
    redis = FakeRedis()
    guard = AuthRateLimiter(
        redis,
        api_key_hashes={"client-a": hash_api_key("live-secret")},
        minute_limit=10,
        hour_limit=10,
    )
    request = _build_request(
        [(b"authorization", b"Bearer invalid")],
        ip="9.9.9.9",
    )
    with pytest.raises(HTTPException):
        await guard.enforce(request)

    assert any(k.startswith("rate:ip:9.9.9.9:minute:") for k in redis.counts)


def test_parse_api_key_hashes_accepts_ids_and_bare_hashes():
    parsed = parse_api_key_hashes("team-a:abc,keyhashonly")
    assert parsed["team-a"] == "abc"
    assert parsed["key2"] == "keyhashonly"


def test_extract_api_key_prefers_bearer_then_x_api_key():
    assert (
        extract_api_key_from_headers(
            {"Authorization": "Bearer abc", "X-API-Key": "xyz"}
        )
        == "abc"
    )
    assert extract_api_key_from_headers({"X-API-Key": "xyz"}) == "xyz"


def test_window_seconds_helpers():
    now = datetime(2026, 1, 1, 12, 34, 10, tzinfo=UTC)
    assert seconds_until_next_minute(now) == 50
    assert seconds_until_next_hour(now) == 1550
