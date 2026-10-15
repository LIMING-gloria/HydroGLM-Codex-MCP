#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3。请先安装 Python 3。" >&2
  exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "需要 Python 3.10 或更高版本。" >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "未找到 Codex 命令。请先安装 Codex CLI，并确保 codex 命令可用。" >&2
  exit 1
fi

agent="${1:-HydroGLM}"
case "$agent" in
  HydroGLM|HydroGLM-plus) ;;
  *) echo "用法：bash setup.sh [HydroGLM|HydroGLM-plus]" >&2; exit 2 ;;
esac

replace_entry=false
if codex mcp list 2>/dev/null | awk '{print $1}' | grep -Fxq hydroglm; then
  printf 'Codex 已有名为 hydroglm 的 MCP。\n'
  read -r -p '是否替换为当前目录中的版本？[y/N] ' answer
  case "$answer" in
    y|Y|yes|YES|Yes) replace_entry=true ;;
    *) echo "未修改现有 MCP。"; exit 0 ;;
  esac
fi

python3 "$SCRIPT_DIR/configure_key.py" --agent "$agent"

if [[ "$replace_entry" == true ]]; then
  codex mcp remove hydroglm
fi

if codex mcp list 2>/dev/null | awk '{print $1}' | grep -Fxq hydroglm; then
  echo "现有 hydroglm MCP 项仍未移除，停止注册。" >&2
  exit 1
fi

codex mcp add hydroglm -- python3 "$SCRIPT_DIR/server.py"

printf '\nHydroGLM MCP 已配置。重启 Codex 后即可调用 ask_hydroglm。\n'
