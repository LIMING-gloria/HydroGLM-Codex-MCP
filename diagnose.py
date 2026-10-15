#!/usr/bin/env python3
"""Check Hanhai agent-key access through the non-generative models endpoint."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from server import AGENTS, read_api_key, request_metadata


MODELS_URL = "https://hanhai-ai.com/api/v1/agent/agent/openai/models"
TIMEOUT_SECONDS = 30


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=list(AGENTS), required=True)
    args = parser.parse_args()

    try:
        key = read_api_key(args.agent)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    request = urllib.request.Request(
        MODELS_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            headers = response.headers
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        headers = exc.headers
        body = exc.read(4096).decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        print(f"Connection failed before receiving an HTTP response: {exc.reason}")
        return 3
    except (TimeoutError, OSError):
        print("Connection timed out before receiving an HTTP response.")
        return 3

    print(f"Agent: {args.agent}")
    print(f"HTTP status: {status}")
    metadata = request_metadata(headers)
    if metadata:
        print(metadata)

    if status == 200:
        try:
            result = json.loads(body)
        except json.JSONDecodeError:
            print("The models endpoint returned HTTP 200 but not valid JSON.")
            return 4
        model_ids = []
        if isinstance(result, dict) and isinstance(result.get("data"), list):
            model_ids = [
                item.get("id")
                for item in result["data"]
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            ]
        print("Key and models endpoint are reachable.")
        if model_ids:
            print("Models: " + ", ".join(model_ids))
        return 0

    try:
        result = json.loads(body)
        error = result.get("error") if isinstance(result, dict) else None
        if isinstance(error, dict):
            code = error.get("code")
            kind = error.get("type")
            message = error.get("message")
            details = [str(x) for x in (code, kind, message) if x]
            if details:
                print("API error: " + " | ".join(details)[:1000])
        elif body.strip():
            print("API response body: " + body.strip()[:1000])
    except json.JSONDecodeError:
        if body.strip():
            print("API response body: " + body.strip()[:1000])

    if status == 401:
        print("Check that this is a valid, newly issued agent key.")
    elif status == 403:
        print("Check that the key is bound to the selected agent.")
    elif status == 504:
        print("The authenticated models request also timed out; this points to a Hanhai gateway/service issue.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
