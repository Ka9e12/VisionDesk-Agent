# VisionDesk Agent

[English README](README.md)

> 一个本地多模态桌面智能体：观察屏幕，调用视觉模型规划步骤，并根据自然语言任务控制键盘和鼠标。

GitHub description:

```text
A local multimodal desktop agent that observes your screen, plans with a vision model, and controls keyboard/mouse from natural-language tasks.
```

VisionDesk Agent 是一个本地 AI 桌面智能体。你给它一句自然语言任务，它会截图观察当前屏幕，调用多模态模型规划下一步，然后模拟鼠标、键盘、快捷键、打开应用、打开网页和等待等操作，循环执行直到任务完成。

## 功能

- 自然语言任务输入
- 多模态模型读屏和规划
- 屏幕截图、当前应用、窗口标题、鼠标位置采集
- 鼠标、键盘、快捷键、滚动、打开应用、打开 URL
- 兼容 OpenAI Chat Completions 风格的多模态接口
- 一键脚本自动创建虚拟环境和安装依赖
- 默认 JPEG 小图模式，降低每步等待时间
- JSONL 执行日志和截图历史
- 可选 OCR、浏览器 DOM、macOS Accessibility、Windows UI Automation
- 默认直接执行模型规划动作，不弹风险确认

## 快速开始

macOS / Linux：

```bash
./mac-agent.sh
```

macOS 双击：

```text
mac-agent.command
```

Windows PowerShell：

```powershell
.\windows-agent.ps1
```

Windows 双击：

```text
windows-agent.bat
```

脚本会自动：

- 创建 `.venv`
- 安装依赖
- 没有 `.env` 时从 `.env.example` 创建
- 首次运行时提示输入 API base URL、模型名和 API Key
- 进入交互模式，直接输入任务即可执行

交互模式示例：

```text
任务> 打开 Safari，搜索 AI Agent 是什么，并总结重点
```

Windows 示例：

```text
任务> 打开 Edge，搜索 AI Agent 是什么，并总结重点
```

## 常用命令

macOS / Linux：

```bash
./mac-agent.sh -help
./mac-agent.sh doctor
./mac-agent.sh perceive
./mac-agent.sh "打开浏览器，搜索 AI 智能体是什么，并总结重点"
./mac-agent.sh run "打开浏览器搜索天气" --dry-run
```

Windows：

```powershell
.\windows-agent.ps1 -help
.\windows-agent.ps1 doctor
.\windows-agent.ps1 perceive
.\windows-agent.ps1 "打开 Edge，搜索 AI 智能体是什么，并总结重点"
.\windows-agent.ps1 run "打开 Edge 搜索天气" --dry-run
```

如果 PowerShell 阻止脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows-agent.ps1
```

## 配置

配置文件是 `.env`，这个文件会被 Git 忽略，不要提交真实密钥。

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

后续换模型，直接改 `.env` 里的：

```text
AGENT_API_BASE=
AGENT_MODEL=
AGENT_API_KEY=
```

也可以使用多个配置文件：

```bash
./mac-agent.sh --env .env.fast
```

```powershell
.\windows-agent.ps1 --env .env.fast
```

## 权限

macOS 需要在系统设置里授权：

```text
系统设置 -> 隐私与安全性 -> 辅助功能
系统设置 -> 隐私与安全性 -> 屏幕录制
```

Windows 一般普通权限即可。如果目标应用是管理员权限启动的，则需要用管理员权限运行 PowerShell 或命令提示符。

## 浏览器 DOM 模式

如果要读取浏览器 DOM，需要用远程调试模式启动 Chrome。

macOS：

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/visiondesk-agent-chrome
```

Windows：

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:TEMP\visiondesk-agent-chrome"
```

然后在 `.env` 里设置：

```text
AGENT_BROWSER_CDP_ENDPOINT=http://127.0.0.1:9222
AGENT_INCLUDE_BROWSER_DOM=true
```

## 速度调优

默认快速模式：

```text
AGENT_SCREENSHOT_MAX_WIDTH=1100
AGENT_SCREENSHOT_FORMAT=jpeg
AGENT_JPEG_QUALITY=70
```

如果还觉得慢，可以降到：

```text
AGENT_SCREENSHOT_MAX_WIDTH=900
AGENT_JPEG_QUALITY=60
```

运行时会打印耗时：

```text
[step 1] observe done 0.50s
[step 1] think done 8.20s
```

如果 `think` 很慢，通常瓶颈是模型接口或网络延迟。

## 项目结构

```text
src/desktop_agent/
  cli.py                  CLI 入口
  controller.py           Observe -> Think -> Act 循环
  config.py               环境变量和运行配置
  schema.py               动作、观察、决策数据结构
  perception/             截图、窗口、OCR、DOM、辅助功能
  planner/                多模态模型调用和提示词
  actions/                本地键鼠和应用执行器
  safety/                 可选风险策略
  memory/                 任务记忆
  runtime/                日志和运行目录
```

启动脚本：

```text
mac-agent.sh              macOS/Linux 终端入口
mac-agent.command         macOS 双击入口
windows-agent.ps1         Windows PowerShell 入口
windows-agent.bat         Windows 双击入口
```

## 开发

手动安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
cp .env.example .env
```

运行测试：

```bash
.venv/bin/python -m pytest
```

构建干净的 zip 包：

```bash
mkdir -p dist
zip -r dist/visiondesk-agent.zip \
  mac-agent.sh mac-agent.command windows-agent.ps1 windows-agent.bat \
  README.md README.zh-CN.md pyproject.toml .env.example .gitignore src tests \
  -x '*/__pycache__/*' '*.DS_Store'
```

## 路线图

- 元素级坐标校准
- 更完整的 macOS 和 Windows 辅助功能树遍历
- 通过 Playwright/CDP 实现更精确的浏览器自动化
- 本地任务模板
- 长期记忆
- 日志可视化回放
