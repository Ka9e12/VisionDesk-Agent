# VisionDesk Agent

[中文文档](README.zh-CN.md)

> A local multimodal desktop agent that observes your screen, plans with a vision model, and controls keyboard/mouse from natural-language tasks.

GitHub description:

```text
A local multimodal desktop agent that observes your screen, plans with a vision model, and controls keyboard/mouse from natural-language tasks.
```

VisionDesk Agent is a local AI desktop agent. Give it a natural-language task, and it will observe the current screen, call a multimodal model to plan the next step, control the mouse/keyboard, and repeat until the task is complete.

## Features

- Natural-language task input
- Multimodal screen understanding
- Screenshot, active app, window title, and mouse position collection
- Mouse, keyboard, hotkey, scroll, app launch, and URL launch actions
- OpenAI-compatible multimodal Chat Completions API
- One-command setup with automatic virtual environment creation
- Fast JPEG screenshot mode for lower latency
- JSONL execution logs and screenshot history
- Optional OCR, browser DOM, macOS Accessibility, and Windows UI Automation probes
- Direct execution mode by default, without risk confirmation prompts

## Quick Start

macOS / Linux:

```bash
./mac-agent.sh
```

macOS double click:

```text
mac-agent.command
```

Windows PowerShell:

```powershell
.\windows-agent.ps1
```

Windows double click:

```text
windows-agent.bat
```

The launcher will automatically:

- create `.venv`
- install dependencies
- create `.env` from `.env.example` if needed
- ask for API base URL, model name, and API key on first run
- enter interactive task mode

Interactive example:

```text
Task> Open Safari, search what AI Agent means, and summarize the key points
```

Windows example:

```text
Task> Open Edge, search what AI Agent means, and summarize the key points
```

## Common Commands

macOS / Linux:

```bash
./mac-agent.sh -help
./mac-agent.sh doctor
./mac-agent.sh perceive
./mac-agent.sh "Open a browser and search what AI agents are"
./mac-agent.sh run "Search the weather in a browser" --dry-run
```

Windows:

```powershell
.\windows-agent.ps1 -help
.\windows-agent.ps1 doctor
.\windows-agent.ps1 perceive
.\windows-agent.ps1 "Open Edge and search what AI agents are"
.\windows-agent.ps1 run "Search the weather in Edge" --dry-run
```

If PowerShell blocks script execution:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows-agent.ps1
```

## Configuration

Configuration lives in `.env`. This file is ignored by Git. Do not commit real API keys.

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

To change model settings later, edit:

```text
AGENT_API_BASE=
AGENT_MODEL=
AGENT_API_KEY=
```

You can also use multiple env files:

```bash
./mac-agent.sh --env .env.fast
```

```powershell
.\windows-agent.ps1 --env .env.fast
```

## Permissions

On macOS, grant permissions in:

```text
System Settings -> Privacy & Security -> Accessibility
System Settings -> Privacy & Security -> Screen Recording
```

On Windows, normal user permissions are usually enough. If the target app is running as Administrator, run PowerShell or Command Prompt as Administrator too.

## Browser DOM Mode

For browser DOM snapshots, start Chrome with remote debugging.

macOS:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/visiondesk-agent-chrome
```

Windows:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:TEMP\visiondesk-agent-chrome"
```

Then set:

```text
AGENT_BROWSER_CDP_ENDPOINT=http://127.0.0.1:9222
AGENT_INCLUDE_BROWSER_DOM=true
```

## Speed Tuning

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

The CLI prints timing information:

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
  perception/             screenshot, window, OCR, DOM, accessibility
  planner/                multimodal model calls and prompts
  actions/                local keyboard/mouse/app executor
  safety/                 optional risk policy
  memory/                 task memory
  runtime/                logs and run directory
```

Launchers:

```text
mac-agent.sh              macOS/Linux terminal launcher
mac-agent.command         macOS double-click launcher
windows-agent.ps1         Windows PowerShell launcher
windows-agent.bat         Windows double-click launcher
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
  mac-agent.sh mac-agent.command windows-agent.ps1 windows-agent.bat \
  README.md README.zh-CN.md pyproject.toml .env.example .gitignore src tests \
  -x '*/__pycache__/*' '*.DS_Store'
```

## Roadmap

- Element-level coordinate calibration
- Better accessibility tree traversal on macOS and Windows
- More precise browser automation through Playwright/CDP
- Local task templates
- Long-term memory
- Visual replay viewer for logs
