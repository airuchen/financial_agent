#!/usr/bin/env python3
"""Interactive streaming chat client for the Financial Research Agent."""

from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RED = "\033[31m"
WHITE = "\033[37m"
BG_DARK = "\033[48;5;236m"


def parse_sse_events(lines: str):
    """Parse raw SSE text into (event_type, data) tuples."""
    event_type = None
    for line in lines.splitlines():
        if line.startswith("event: "):
            event_type = line[7:].strip()
        elif line.startswith("data: "):
            raw = line[6:]
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = raw
            yield event_type, data
            event_type = None


def print_badge(label: str, value: str, color: str):
    sys.stdout.write(f"  {DIM}{color}{label}:{RESET} {color}{value}{RESET}")


def stream_query(url: str, query: str, api_key: str | None) -> None:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"query": query, "stream": True}
    start = time.monotonic()
    route = ""
    cache_hit = False
    cache_tier = "none"
    sources: list[dict] = []
    token_count = 0

    try:
        with httpx.stream(
            "POST",
            f"{url}/query",
            json=payload,
            headers=headers,
            timeout=60.0,
        ) as response:
            if response.status_code != 200:
                body = response.read().decode()
                print(f"\n{RED}Error {response.status_code}:{RESET} {body}")
                return

            sys.stdout.write(f"\n{GREEN}{BOLD}Agent:{RESET} ")
            sys.stdout.flush()

            buffer = ""
            for chunk in response.iter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)
                    for event_type, data in parse_sse_events(event_block):
                        if event_type == "route" and isinstance(data, dict):
                            route = data.get("route", "")

                        elif event_type == "meta" and isinstance(data, dict):
                            cache_hit = data.get("cache_hit", False)
                            cache_tier = data.get("cache_tier", "none")

                        elif event_type == "token" and isinstance(data, dict):
                            content = data.get("content", "")
                            sys.stdout.write(content)
                            sys.stdout.flush()
                            token_count += 1

                        elif event_type == "sources" and isinstance(data, dict):
                            sources = data.get("sources", [])

                        elif event_type == "done":
                            pass

    except httpx.ConnectError:
        print(f"\n{RED}Connection refused.{RESET} Is the server running at {url}?")
        return
    except httpx.ReadTimeout:
        print(f"\n{RED}Request timed out.{RESET}")
        return
    except KeyboardInterrupt:
        pass

    elapsed = time.monotonic() - start

    # Newline after streamed content
    sys.stdout.write("\n")

    # Sources
    if sources:
        sys.stdout.write(f"\n{DIM}Sources:{RESET}\n")
        for i, src in enumerate(sources, 1):
            title = src.get("title", "Untitled")
            link = src.get("url", "")
            sys.stdout.write(f"  {DIM}[{i}]{RESET} {CYAN}{title}{RESET}")
            if link:
                sys.stdout.write(f"  {DIM}{link}{RESET}")
            sys.stdout.write("\n")

    # Metadata badges
    sys.stdout.write("\n")
    route_color = MAGENTA if route == "search" else BLUE
    print_badge("route", route, route_color)

    cache_color = GREEN if cache_hit else DIM
    cache_label = f"hit ({cache_tier})" if cache_hit else "miss"
    print_badge("cache", cache_label, cache_color)

    print_badge("time", f"{elapsed:.1f}s", YELLOW)
    sys.stdout.write("\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive chat client for the Financial Research Agent"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for authenticated requests",
    )
    args = parser.parse_args()

    print(f"{BOLD}Financial Research Agent{RESET}")
    print(f"{DIM}Server: {args.url}{RESET}")
    print(f"{DIM}Type /quit to exit, Ctrl+C to cancel a request{RESET}\n")

    while True:
        try:
            query = input(f"{CYAN}{BOLD}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Bye.{RESET}")
            break

        if not query:
            continue
        if query in ("/quit", "/exit", "/q"):
            print(f"{DIM}Bye.{RESET}")
            break

        stream_query(args.url, query, args.api_key)


if __name__ == "__main__":
    main()
