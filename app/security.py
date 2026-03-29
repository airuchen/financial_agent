import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class AuthResult:
    is_valid: bool
    key_id: str | None
    provided: bool


@dataclass(frozen=True)
class RateLimitResult:
    minute_count: int
    hour_count: int
    minute_remaining: int
    hour_remaining: int
    minute_ttl: int
    hour_ttl: int

    @property
    def is_limited(self) -> bool:
        return self.minute_remaining < 0 or self.hour_remaining < 0

    @property
    def retry_after(self) -> int:
        if self.minute_remaining < 0 and self.hour_remaining < 0:
            return min(self.minute_ttl, self.hour_ttl)
        if self.minute_remaining < 0:
            return self.minute_ttl
        return self.hour_ttl


class AuthRateLimiter:
    """Authenticate API keys and enforce Redis-backed rate limits."""

    def __init__(
        self,
        redis_client,
        *,
        api_key_hashes: dict[str, str],
        minute_limit: int,
        hour_limit: int,
    ):
        self.redis = redis_client
        self.api_key_hashes = api_key_hashes
        self.minute_limit = minute_limit
        self.hour_limit = hour_limit

    @classmethod
    async def create(
        cls,
        *,
        redis_url: str,
        api_key_hashes_raw: str,
        minute_limit: int,
        hour_limit: int,
    ):
        from redis.asyncio import Redis

        redis_client = Redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        api_key_hashes = parse_api_key_hashes(api_key_hashes_raw)
        return cls(
            redis_client,
            api_key_hashes=api_key_hashes,
            minute_limit=minute_limit,
            hour_limit=hour_limit,
        )

    async def enforce(self, request: Request) -> None:
        client_ip = _extract_client_ip(request)
        auth = self._authenticate_request(request)
        scope = auth.key_id if auth.is_valid and auth.key_id else f"ip:{client_ip}"

        try:
            rate = await self._check_rate_limit(scope)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "rate_limiter_unavailable",
                    "message": "Rate-limiting backend unavailable; retry later.",
                },
            ) from exc

        if rate.is_limited:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "rate_limit_exceeded",
                    "message": "Too many requests. Please retry later.",
                },
                headers={
                    "Retry-After": str(rate.retry_after),
                    "X-RateLimit-Limit-Minute": str(self.minute_limit),
                    "X-RateLimit-Remaining-Minute": str(max(0, rate.minute_remaining)),
                    "X-RateLimit-Limit-Hour": str(self.hour_limit),
                    "X-RateLimit-Remaining-Hour": str(max(0, rate.hour_remaining)),
                    "X-RateLimit-Scope": scope,
                },
            )

        if not auth.is_valid:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "unauthorized",
                    "message": "Missing or invalid API key.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _authenticate_request(self, request: Request) -> AuthResult:
        api_key = extract_api_key_from_headers(request.headers)
        if not api_key:
            return AuthResult(is_valid=False, key_id=None, provided=False)

        provided_hash = hash_api_key(api_key)
        matched_id = None
        for key_id, expected_hash in self.api_key_hashes.items():
            if hmac.compare_digest(provided_hash, expected_hash):
                matched_id = key_id
        if matched_id:
            return AuthResult(is_valid=True, key_id=matched_id, provided=True)
        return AuthResult(is_valid=False, key_id=None, provided=True)

    async def _check_rate_limit(self, scope: str) -> RateLimitResult:
        now = datetime.now(UTC)
        minute_bucket = now.strftime("%Y%m%d%H%M")
        hour_bucket = now.strftime("%Y%m%d%H")

        minute_key = f"rate:{scope}:minute:{minute_bucket}"
        hour_key = f"rate:{scope}:hour:{hour_bucket}"

        minute_ttl = seconds_until_next_minute(now)
        hour_ttl = seconds_until_next_hour(now)

        minute_count = await self._incr_window(minute_key, minute_ttl)
        hour_count = await self._incr_window(hour_key, hour_ttl)

        return RateLimitResult(
            minute_count=minute_count,
            hour_count=hour_count,
            minute_remaining=self.minute_limit - minute_count,
            hour_remaining=self.hour_limit - hour_count,
            minute_ttl=minute_ttl,
            hour_ttl=hour_ttl,
        )

    async def _incr_window(self, key: str, ttl_seconds: int) -> int:
        pipe = self.redis.pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, ttl_seconds, nx=True)
        result = await pipe.execute()
        return int(result[0])


class UnavailableGuard:
    """Fail-closed guard used when Redis is not available at startup."""

    async def enforce(self, request: Request) -> None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "rate_limiter_unavailable",
                "message": "Rate-limiting backend unavailable; retry later.",
            },
        )


def parse_api_key_hashes(raw: str) -> dict[str, str]:
    """Parse API key hashes from `id:sha256` comma-separated env format."""
    entries = [e.strip() for e in raw.split(",") if e.strip()]
    parsed: dict[str, str] = {}
    for idx, entry in enumerate(entries, start=1):
        if ":" in entry:
            key_id, key_hash = entry.split(":", maxsplit=1)
        else:
            key_id, key_hash = f"key{idx}", entry
        parsed[key_id.strip()] = key_hash.strip().lower()
    return parsed


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def extract_api_key_from_headers(headers) -> str | None:
    auth_header = headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer_key = auth_header.removeprefix("Bearer ").strip()
        if bearer_key:
            return bearer_key
    x_api_key = headers.get("X-API-Key", "").strip()
    if x_api_key:
        return x_api_key
    return None


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def seconds_until_next_minute(now: datetime) -> int:
    return 60 - now.second


def seconds_until_next_hour(now: datetime) -> int:
    return ((59 - now.minute) * 60) + (60 - now.second)
