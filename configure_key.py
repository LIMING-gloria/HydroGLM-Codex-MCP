#!/usr/bin/env python3
"""Save a Hanhai agent key in a private user config file without echoing it."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import tempfile
from pathlib import Path


AGENTS = {
    "HydroGLM": "hydroglm",
    "HydroGLM-plus": "hydroglm_plus",
}


def config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hydroglm-mcp"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=list(AGENTS), required=True)
    args = parser.parse_args()

    key = getpass.getpass(f"Enter a newly issued API key for {args.agent}: ").strip()
    if not key:
        parser.error("API key cannot be empty")
    if not key.startswith("sk-"):
        parser.error("The key should start with sk-; check that you copied the agent key")

    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    path = directory / "credentials.json"

    credentials: dict[str, str] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            parser.error(f"Could not read existing credentials file: {path}")
        if not isinstance(existing, dict):
            parser.error(f"Existing credentials file must contain a JSON object: {path}")
        credentials = {
            name: value
            for name, value in existing.items()
            if name in AGENTS.values() and isinstance(value, str)
        }

    credentials[AGENTS[args.agent]] = key
    fd, temporary_name = tempfile.mkstemp(prefix="credentials.", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as temporary_file:
            json.dump(credentials, temporary_file, ensure_ascii=False)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)

    print(f"Saved the {args.agent} key in {path} with owner-only permissions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
