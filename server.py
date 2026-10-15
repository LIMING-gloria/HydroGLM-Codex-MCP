#!/usr/bin/env python3
"""A small, dependency-free stdio MCP server for the Hanhai HydroGLM API."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SERVER_NAME = "hydroglm"
SERVER_VERSION = "0.1.0"
API_URL = "https://hanhai-ai.com/api/v1/agent/agent/openai/chat/completions"
MODELS_URL = "https://hanhai-ai.com/api/v1/agent/agent/openai/models"
MAX_QUESTION_CHARS = 20_000
REQUEST_TIMEOUT_SECONDS = 180

AGENTS = {
    "HydroGLM": ("hydroglm", "HANHAI_HYDROGLM_API_KEY"),
    "HydroGLM-plus": ("hydroglm_plus", "HANHAI_HYDROGLM_PLUS_API_KEY"),
}


def credentials_path() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "hydroglm-mcp" / "credentials.json"


def read_api_key(agent: str) -> str:
    credential_name, env_name = AGENTS[agent]
    value = os.environ.get(env_name, "").strip()
    if value:
        return value

    path = credentials_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"No key is configured for {agent}. Run configure_key.py --agent {agent}."
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Could not read the HydroGLM credentials file at {path}. "
            "Reconfigure the key with configure_key.py."
        ) from exc

    value = data.get(credential_name, "") if isinstance(data, dict) else ""
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"No key is configured for {agent}. Run configure_key.py --agent {agent}."
        )
    return value.strip()


def api_error_message(status: int) -> str:
    if status == 401:
        return "HydroGLM rejected the key (HTTP 401). Check or replace the configured key."
    if status == 403:
        return "HydroGLM rejected this key for the selected agent (HTTP 403). " \
            "Use a key bound to the same agent."
    if status == 429:
        return "HydroGLM rate limit reached (HTTP 429). Try again later."
    if status >= 500:
        return f"HydroGLM service returned HTTP {status}. Try again later."
    return f"HydroGLM request failed with HTTP {status}. Check the request settings."


def request_metadata(headers: Any) -> str:
    """Return only safe correlation metadata from an upstream response."""
    parts = []
    for name in ("x-request-id", "request-id", "x-trace-id", "traceparent", "date", "retry-after"):
        value = headers.get(name) if headers else None
        if value:
            parts.append(f"{name}: {value}")
    return "\n".join(parts)


def call_hydroglm(arguments: dict[str, Any]) -> str:
    question = arguments.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    question = question.strip()
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"question must be at most {MAX_QUESTION_CHARS} characters")

    agent = arguments.get("agent", "HydroGLM")
    if agent not in AGENTS:
        raise ValueError("agent must be HydroGLM or HydroGLM-plus")

    payload: dict[str, Any] = {
        "model": agent,
        "stream": False,
        "messages": [{"role": "user", "content": question}],
    }
    session_id = arguments.get("session_id")
    if session_id is not None:
        if isinstance(session_id, bool) or not isinstance(session_id, int) or session_id < 0:
            raise ValueError("session_id must be a non-negative integer")
        payload["session_id"] = session_id

    for name in ("web_search", "enable_thinking"):
        if name in arguments:
            if not isinstance(arguments[name], bool):
                raise ValueError(f"{name} must be true or false")
            payload[name] = arguments[name]

    api_key = read_api_key(agent)
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = request_metadata(exc.headers)
        message = api_error_message(exc.code)
        if details:
            message += f"\nUpstream diagnostics:\n{details}"
        raise RuntimeError(message) from None
    except urllib.error.URLError:
        raise RuntimeError("Could not connect to the HydroGLM API. Check network access.") from None
    except (TimeoutError, OSError):
        raise RuntimeError("The HydroGLM API request timed out or the connection failed.") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("HydroGLM returned a response that was not valid JSON.") from None

    try:
        choice = result["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("HydroGLM returned an unexpected response format.") from None

    if isinstance(content, str):
        answer = content
    elif isinstance(content, list):
        answer = "\n".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        )
    else:
        answer = ""
    if not answer.strip():
        raise RuntimeError("HydroGLM returned an empty answer.")

    returned_session_id = result.get("session_id")
    if returned_session_id is not None:
        answer += f"\n\nHydroGLM session_id: {returned_session_id}"
    return answer


TOOL = {
    "name": "ask_hydroglm",
    "description": (
        "Ask the Hanhai HydroGLM water-domain agent. The question is sent to the "
        "Hanhai API. Choose the agent whose API key is configured. For a follow-up, "
        "pass the session_id returned by the previous call. This API does not expose "
        "function calling; this MCP tool returns the agent's answer as text."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to send to HydroGLM.",
            },
            "agent": {
                "type": "string",
                "enum": ["HydroGLM", "HydroGLM-plus"],
                "default": "HydroGLM",
                "description": "The agent matching the configured Hanhai API key.",
            },
            "session_id": {
                "type": "integer",
                "minimum": 0,
                "description": "Optional session_id from an earlier HydroGLM response.",
            },
            "web_search": {
                "type": "boolean",
                "description": "Enable Hanhai web search for this request.",
            },
            "enable_thinking": {
                "type": "boolean",
                "description": "Enable the agent's thinking mode for this request.",
            },
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}


def rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_request(message: Any) -> dict[str, Any] | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return rpc_error(None, -32600, "Invalid Request")

    method = message.get("method")
    request_id = message.get("id")
    is_notification = "id" not in message
    params = message.get("params", {})
    if not isinstance(params, dict):
        if is_notification:
            return None
        return rpc_error(request_id, -32602, "Invalid params")

    if method == "initialize":
        client_version = params.get("protocolVersion", "2024-11-05")
        return rpc_result(
            request_id,
            {
                "protocolVersion": client_version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None

    if method == "ping":
        return None if is_notification else rpc_result(request_id, {})

    if method == "tools/list":
        return None if is_notification else rpc_result(request_id, {"tools": [TOOL]})

    if method == "tools/call":
        if is_notification:
            return None
        if params.get("name") != TOOL["name"]:
            return rpc_error(request_id, -32602, "Unknown tool")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return rpc_error(request_id, -32602, "Tool arguments must be an object")
        try:
            answer = call_hydroglm(arguments)
        except (ValueError, RuntimeError) as exc:
            return rpc_result(
                request_id,
                {"content": [{"type": "text", "text": str(exc)}], "isError": True},
            )
        return rpc_result(
            request_id,
            {"content": [{"type": "text", "text": answer}], "isError": False},
        )

    if is_notification:
        return None
    return rpc_error(request_id, -32601, "Method not found")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            response = handle_request(message)
        except json.JSONDecodeError:
            response = rpc_error(None, -32700, "Parse error")
        except Exception:
            # Keep stdout protocol-only and avoid logging request contents or secrets.
            response = rpc_error(None, -32603, "Internal server error")
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
