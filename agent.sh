#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/.env"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

print_help() {
  cat <<'EOF'
VisionDesk Agent 一键脚本

用法：
  ./agent.sh                         自动配置后进入交互模式
  ./agent.sh "你的任务"               直接执行一个任务
  ./agent.sh run "你的任务" [参数]     直接透传到 desktop-agent run
  ./agent.sh doctor                  检查环境
  ./agent.sh perceive                截图并输出当前感知
  ./agent.sh setup                   只安装/修复环境，不执行任务
  ./agent.sh cli [desktop-agent参数]  使用原始 CLI
  ./agent.sh -help                   显示帮助

常用参数：
  --env FILE                         使用指定 env 文件，默认 .env
  --dry-run                          只规划不实际点击/输入，需要配合 run
  --ocr                              启用 OCR，需要配合 run/perceive
  --browser-dom                      启用浏览器 DOM，需要配合 run/perceive
  --accessibility                    启用 macOS Accessibility，需要配合 run/perceive

交互模式命令：
  直接输入任务                        执行任务
  doctor                             检查环境
  perceive                           感知当前屏幕
  help                               显示帮助
  exit                               退出

例子：
  ./agent.sh
  ./agent.sh "打开 Safari 搜索 AI Agent，并总结重点"
  ./agent.sh run "打开备忘录写一条测试笔记" --dry-run
EOF
}

log() {
  printf '[agent] %s\n' "$1"
}

set_env_value() {
  local key="$1"
  local value="$2"
  "$PYTHON_BIN" - "$ENV_FILE" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
line = f"{key}={value}"

lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
updated = False
out = []
for old in lines:
    if old.startswith(key + "="):
        out.append(line)
        updated = True
    else:
        out.append(old)
if not updated:
    out.append(line)
path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
PY
}

env_value() {
  local key="$1"
  if [[ ! -f "$ENV_FILE" ]]; then
    return 0
  fi
  grep -E "^${key}=" "$ENV_FILE" | tail -1 | cut -d= -f2- || true
}

ensure_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$ROOT_DIR/.env.example" ]]; then
      cp "$ROOT_DIR/.env.example" "$ENV_FILE"
    else
      touch "$ENV_FILE"
    fi
    log "已创建 $ENV_FILE"
  fi

  local api_key api_base model
  api_key="$(env_value AGENT_API_KEY)"
  api_base="$(env_value AGENT_API_BASE)"
  model="$(env_value AGENT_MODEL)"

  if [[ -z "$api_base" || "$api_base" == "https://api.openai.com/v1" ]]; then
    read -r -p "模型接口 base_url [http://tw.saviora.space:9999]: " api_base
    api_base="${api_base:-http://tw.saviora.space:9999}"
    set_env_value AGENT_API_BASE "$api_base"
  fi

  if [[ -z "$model" || "$model" == "replace_with_multimodal_model" ]]; then
    read -r -p "模型名称 [gpt-5.5]: " model
    model="${model:-gpt-5.5}"
    set_env_value AGENT_MODEL "$model"
  fi

  if [[ -z "$api_key" || "$api_key" == "replace_me" ]]; then
    read -r -s -p "API Key: " api_key
    printf '\n'
    if [[ -z "$api_key" ]]; then
      log "缺少 API Key，稍后可以编辑 $ENV_FILE 再运行。"
    else
      set_env_value AGENT_API_KEY "$api_key"
    fi
  fi

  if [[ -z "$(env_value AGENT_REQUIRE_CONFIRMATION)" ]]; then
    set_env_value AGENT_REQUIRE_CONFIRMATION "false"
  fi
  if [[ -z "$(env_value AGENT_SCREENSHOT_MAX_WIDTH)" ]]; then
    set_env_value AGENT_SCREENSHOT_MAX_WIDTH "1100"
  fi
  if [[ -z "$(env_value AGENT_SCREENSHOT_FORMAT)" ]]; then
    set_env_value AGENT_SCREENSHOT_FORMAT "jpeg"
  fi
  if [[ -z "$(env_value AGENT_JPEG_QUALITY)" ]]; then
    set_env_value AGENT_JPEG_QUALITY "70"
  fi
}

deps_ready() {
  [[ -x "$VENV_DIR/bin/python" ]] || return 1
  "$VENV_DIR/bin/python" - <<'PY' >/dev/null 2>&1
import importlib.util
mods = [
    "desktop_agent",
    "pyautogui",
    "mss",
    "PIL",
    "pytesseract",
    "playwright",
    "ApplicationServices",
]
missing = [name for name in mods if importlib.util.find_spec(name) is None]
raise SystemExit(1 if missing else 0)
PY
}

pip_install() {
  local pip="$VENV_DIR/bin/python -m pip"
  if ! $pip install "$@"; then
    log "普通 pip 安装失败，使用 trusted-host 重试。"
    $pip install "$@" --trusted-host pypi.org --trusted-host files.pythonhosted.org
  fi
}

ensure_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    log "首次运行，正在创建虚拟环境..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  if deps_ready; then
    return 0
  fi

  log "正在安装/修复依赖，第一次会稍慢..."
  pip_install --upgrade pip
  pip_install -e ".[all]"
}

desktop_agent() {
  "$VENV_DIR/bin/desktop-agent" --env "$ENV_FILE" "$@"
}

bootstrap() {
  ensure_env_file
  ensure_venv
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}

run_task() {
  local task="$*"
  if [[ -z "$task" ]]; then
    return 0
  fi
  desktop_agent run "$task"
}

interactive_loop() {
  cat <<'EOF'

VisionDesk Agent 已准备好。
直接输入任务即可执行；输入 help 查看命令；输入 exit 退出。
EOF
  while true; do
    printf '\n任务> '
    if ! IFS= read -r task; then
      printf '\n'
      break
    fi
    case "$task" in
      "")
        continue
        ;;
      exit|quit|q)
        break
        ;;
      help|-help|--help)
        print_help
        ;;
      doctor)
        desktop_agent doctor || true
        ;;
      perceive)
        desktop_agent perceive --accessibility || true
        ;;
      *)
        desktop_agent run "$task" || true
        ;;
    esac
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env|-e)
      ENV_FILE="$ROOT_DIR/${2:-.env}"
      if [[ "$ENV_FILE" = /* ]]; then
        ENV_FILE="$2"
      fi
      shift 2
      ;;
    -help|--help|help)
      print_help
      exit 0
      ;;
    *)
      break
      ;;
  esac
done

bootstrap

if [[ $# -eq 0 ]]; then
  interactive_loop
  exit 0
fi

case "$1" in
  setup|-setup|--setup)
    log "环境已准备好。"
    ;;
  doctor|-doctor|--doctor)
    desktop_agent doctor
    ;;
  perceive|-perceive|--perceive)
    shift
    if [[ $# -eq 0 ]]; then
      desktop_agent perceive --accessibility
    else
      desktop_agent perceive "$@"
    fi
    ;;
  run)
    shift
    desktop_agent run "$@"
    ;;
  cli)
    shift
    desktop_agent "$@"
    ;;
  *)
    run_task "$@"
    ;;
esac
