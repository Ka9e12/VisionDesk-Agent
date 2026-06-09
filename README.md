# VisionDesk Agent

> A local multimodal desktop agent that observes your screen, plans with a vision model, and controls keyboard/mouse from natural-language tasks.

VisionDesk Agent 是一个本地 AI 桌面智能体。你给它一句自然语言任务，它会截图观察当前屏幕，调用多模态模型规划下一步，然后模拟鼠标、键盘、快捷键、打开应用和等待等操作，循环执行直到任务完成。

GitHub description 建议使用：

```text
A local multimodal desktop agent that observes your screen, plans with a vision model, and controls keyboard/mouse from natural-language tasks.
```

## Features

- Natural-language task input
- Multimodal screen understanding
- Screenshot, active app, window title, mouse position collection
- Mouse, keyboard, hotkey, scroll, app launch, URL launch actions
- OpenAI-compatible multimodal model API
- One-command setup with automatic virtual environment creation
- Fast JPEG screenshot mode for lower latency
- JSONL execution logs and screenshot history
- Optional OCR, browser DOM, and macOS Accessibility probes
- Direct execution mode by default, without risk confirmation prompts

## Quick Start

Clone or download this project, then run:

```bash
./agent.sh
```

The script will automatically:

- create `.venv` if it does not exist
- install all dependencies
- create `.env` from `.env.example` if needed
- ask for API base URL, model name, and API key on first run
- enter interactive task mode

After startup, type a task directly:

```text
任务> 打开 Safari，搜索 AI Agent 是什么，并总结重点
```

## macOS Double Click

On macOS, you can also double-click:

```text
run-agent.command
```

If macOS blocks execution, run once in terminal:

```bash
chmod +x agent.sh run-agent.command
```

## Configuration

Configuration lives in `.env`.

Example:

```text
AGENT_API_BASE=http://your-api-host:9999
AGENT_MODEL=gpt-5.5
AGENT_API_KEY=your_api_key

AGENT_MAX_STEPS=30
AGENT_DRY_RUN=false
AGENT_REQUIRE_CONFIRMATION=false
AGENT_SCREENSHOT_MAX_WIDTH=1100
AGENT_SCREENSHOT_FORMAT=jpeg
AGENT_JPEG_QUALITY=70
```

Important:

- `.env` is ignored by Git.
- Do not commit your real API key.
- `.env.example` should only contain placeholders or safe defaults.

To change model settings later, edit `.env` and run `./agent.sh` again.

You can also use another env file:

```bash
./agent.sh --env .env.fast
./agent.sh --env .env.smart
```

## Usage

Interactive mode:

```bash
./agent.sh
```

Run one task directly:

```bash
./agent.sh "打开浏览器，搜索 AI 智能体是什么，并总结重点"
```

Check the local environment:

```bash
./agent.sh doctor
```

Capture one observation:

```bash
./agent.sh perceive
```

Show help:

```bash
./agent.sh -help
```

Use the original CLI:

```bash
./agent.sh cli run "打开备忘录，写一条测试笔记"
```

Dry run:

```bash
./agent.sh run "打开浏览器搜索天气" --dry-run
```

Enable stronger perception:

```bash
./agent.sh run "整理当前网页里的表格信息" --ocr --browser-dom --accessibility
```

## Permissions

On macOS, desktop automation usually needs permissions:

```text
System Settings -> Privacy & Security -> Accessibility
System Settings -> Privacy & Security -> Screen Recording
```

Grant permission to the terminal app, Python, or the app you use to run this project.

## Browser DOM Mode

For browser DOM snapshots, start Chrome with remote debugging:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/visiondesk-agent-chrome
```

Then set:

```text
AGENT_BROWSER_CDP_ENDPOINT=http://127.0.0.1:9222
AGENT_INCLUDE_BROWSER_DOM=true
```

## Speed Tuning

Vision models can be slow because every step may require a screenshot upload and model response.

Default fast mode:

```text
AGENT_SCREENSHOT_MAX_WIDTH=1100
AGENT_SCREENSHOT_FORMAT=jpeg
AGENT_JPEG_QUALITY=70
```

For faster but less detailed vision:

```text
AGENT_SCREENSHOT_MAX_WIDTH=900
AGENT_JPEG_QUALITY=60
```

When running tasks, the CLI prints timing information:

```text
[step 1] observe done 0.50s
[step 1] think done 8.20s
```

If `think` is slow, the bottleneck is usually the model endpoint or network latency.

## Project Structure

```text
src/desktop_agent/
  cli.py                  CLI entry
  controller.py           Observe -> Think -> Act loop
  config.py               env and runtime configuration
  schema.py               action, observation, decision data structures
  perception/             screenshot, window, OCR, DOM, Accessibility
  planner/                multimodal model calls and prompts
  actions/                local keyboard/mouse/app executor
  safety/                 optional risk policy
  memory/                 task memory
  runtime/                logs and run directory
```

## Development

Manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
cp .env.example .env
```

Run tests:

```bash
.venv/bin/python -m pytest
```

Build a clean zip package:

```bash
mkdir -p dist
zip -r dist/visiondesk-agent.zip \
  agent.sh run-agent.command README.md pyproject.toml .env.example .gitignore src tests \
  -x '*/__pycache__/*' '*.DS_Store'
```

## Notes

VisionDesk Agent is designed as a practical local automation prototype. Reliability depends on:

- the multimodal model's screen understanding and coordinate accuracy
- desktop permissions
- target app behavior
- network latency to the model endpoint

The default configuration executes model-planned actions directly. Use `--dry-run` when testing new workflows.

## Roadmap

- Element-level coordinate calibration
- Better macOS Accessibility tree traversal
- More precise browser automation through Playwright/CDP
- Local task templates
- Long-term memory
- Visual replay viewer for logs
