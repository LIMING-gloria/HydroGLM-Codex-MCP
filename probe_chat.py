#!/usr/bin/env python3
"""Send one small Chat Completions request and print safe diagnostic details."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from server import AGENTS, API_URL, REQUEST_TIMEOUT_SECONDS, read_api_key, request_metadata


DEFAULT_QUESTION = "请用一句话说明水库汛限水位的作用。"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=list(AGENTS), required=True)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    args = parser.parse_args()

    try:
        key = read_api_key(args.agent)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload = {
        "model": args.agent,
        "stream": False,
        "messages": [{"role": "user", "content": args.question}],
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    print("Local time: " + datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"))
    print(f"Agent: {args.agent}")
    print("Endpoint: POST /api/v1/agent/agent/openai/chat/completions")
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status = response.status
            headers = response.headers
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        headers = exc.headers
        body = exc.read(4096).decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        print(f"No HTTP response; connection failed: {exc.reason}")
        return 3
    except (TimeoutError, OSError):
        print("No HTTP response; the connection timed out or failed.")
        return 3

    print(f"HTTP status: {status}")
    metadata = request_metadata(headers)
    if metadata:
        print(metadata)

    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        if body.strip():
            print("Response body: " + body.strip()[:2000])
        return 0 if 200 <= status < 300 else 1

    if 200 <= status < 300:
        try:
            answer = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            print("The endpoint returned success but an unexpected response shape.")
            print("Response body: " + json.dumps(result, ensure_ascii=False)[:2000])
            return 4
        print("Answer:")
        print(answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False))
        if result.get("session_id") is not None:
            print(f"session_id: {result['session_id']}")
        return 0

    error = result.get("error") if isinstance(result, dict) else None
    if isinstance(error, dict):
        print("API error:")
        for name in ("type", "code", "message"):
            value = error.get(name)
            if value:
                print(f"  {name}: {str(value)[:1000]}")
    else:
        print("Response body: " + json.dumps(result, ensure_ascii=False)[:2000])

    if status == 401:
        print("Check whether the key is valid and has not been revoked.")
    elif status == 403:
        print("Check whether the key is bound to the selected agent.")
    elif status == 504:
        print("The gateway timed out on the chat endpoint. Give Hanhai support the request ID and local timestamp above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
