$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

$EnvFile = Join-Path $RootDir ".env"
$VenvDir = Join-Path $RootDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

function Show-Help {
@"
VisionDesk Agent Windows 一键脚本

用法：
  .\windows-agent.ps1                         自动配置后进入交互模式
  .\windows-agent.ps1 "你的任务"               直接执行一个任务
  .\windows-agent.ps1 run "你的任务" [参数]     直接透传到 desktop-agent run
  .\windows-agent.ps1 doctor                  检查环境
  .\windows-agent.ps1 perceive                截图并输出当前感知
  .\windows-agent.ps1 setup                   只安装/修复环境，不执行任务
  .\windows-agent.ps1 cli [desktop-agent参数]  使用原始 CLI
  .\windows-agent.ps1 -help                   显示帮助

常用参数：
  --env FILE                          使用指定 env 文件，默认 .env
  --dry-run                           只规划不实际点击/输入，需要配合 run
  --ocr                               启用 OCR，需要配合 run/perceive
  --browser-dom                       启用浏览器 DOM，需要配合 run/perceive
  --accessibility                     启用 Windows UI Automation，需要配合 run/perceive

交互模式命令：
  直接输入任务                         执行任务
  doctor                              检查环境
  perceive                            感知当前屏幕
  help                                显示帮助
  exit                                退出

例子：
  .\windows-agent.ps1
  .\windows-agent.ps1 "打开 Edge 搜索 AI Agent，并总结重点"
  .\windows-agent.ps1 run "打开记事本写一条测试笔记" --dry-run
"@
}

function Write-AgentLog([string]$Message) {
  Write-Host "[agent] $Message"
}

function Invoke-SystemPython {
  param([string[]]$PythonArgs)

  if (Get-Command python -ErrorAction SilentlyContinue) {
    & python @PythonArgs
    return
  }
  if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @PythonArgs
    return
  }
  throw "没有找到 Python。请先安装 Python 3.11+，并勾选 Add python.exe to PATH。"
}

function Get-EnvValue([string]$Key) {
  if (-not (Test-Path -LiteralPath $EnvFile)) {
    return ""
  }
  $line = Get-Content -LiteralPath $EnvFile | Where-Object { $_ -like "$Key=*" } | Select-Object -Last 1
  if (-not $line) {
    return ""
  }
  return $line.Substring($Key.Length + 1)
}

function Set-EnvValue([string]$Key, [string]$Value) {
  $line = "$Key=$Value"
  $lines = @()
  if (Test-Path -LiteralPath $EnvFile) {
    $lines = @(Get-Content -LiteralPath $EnvFile)
  }

  $updated = $false
  $out = foreach ($old in $lines) {
    if ($old -like "$Key=*") {
      $updated = $true
      $line
    } else {
      $old
    }
  }
  if (-not $updated) {
    $out += $line
  }
  Set-Content -LiteralPath $EnvFile -Value $out -Encoding UTF8
}

function Convert-SecureStringToPlain([securestring]$Secure) {
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
  }
}

function Ensure-EnvFile {
  if (-not (Test-Path -LiteralPath $EnvFile)) {
    $example = Join-Path $RootDir ".env.example"
    if (Test-Path -LiteralPath $example) {
      Copy-Item -LiteralPath $example -Destination $EnvFile
    } else {
      New-Item -ItemType File -Path $EnvFile | Out-Null
    }
    Write-AgentLog "已创建 $EnvFile"
  }

  $apiBase = Get-EnvValue "AGENT_API_BASE"
  $model = Get-EnvValue "AGENT_MODEL"
  $apiKey = Get-EnvValue "AGENT_API_KEY"

  if ([string]::IsNullOrWhiteSpace($apiBase) -or $apiBase -eq "https://api.openai.com/v1") {
    $inputValue = Read-Host "模型接口 base_url [http://tw.saviora.space:9999]"
    if ([string]::IsNullOrWhiteSpace($inputValue)) {
      $inputValue = "http://tw.saviora.space:9999"
    }
    Set-EnvValue "AGENT_API_BASE" $inputValue
  }

  if ([string]::IsNullOrWhiteSpace($model) -or $model -eq "replace_with_multimodal_model") {
    $inputValue = Read-Host "模型名称 [gpt-5.5]"
    if ([string]::IsNullOrWhiteSpace($inputValue)) {
      $inputValue = "gpt-5.5"
    }
    Set-EnvValue "AGENT_MODEL" $inputValue
  }

  if ([string]::IsNullOrWhiteSpace($apiKey) -or $apiKey -eq "replace_me") {
    $secure = Read-Host "API Key" -AsSecureString
    $plain = Convert-SecureStringToPlain $secure
    if ([string]::IsNullOrWhiteSpace($plain)) {
      Write-AgentLog "缺少 API Key，稍后可以编辑 $EnvFile 再运行。"
    } else {
      Set-EnvValue "AGENT_API_KEY" $plain
    }
  }

  if ([string]::IsNullOrWhiteSpace((Get-EnvValue "AGENT_REQUIRE_CONFIRMATION"))) {
    Set-EnvValue "AGENT_REQUIRE_CONFIRMATION" "false"
  }
  if ([string]::IsNullOrWhiteSpace((Get-EnvValue "AGENT_SCREENSHOT_MAX_WIDTH"))) {
    Set-EnvValue "AGENT_SCREENSHOT_MAX_WIDTH" "1100"
  }
  if ([string]::IsNullOrWhiteSpace((Get-EnvValue "AGENT_SCREENSHOT_FORMAT"))) {
    Set-EnvValue "AGENT_SCREENSHOT_FORMAT" "jpeg"
  }
  if ([string]::IsNullOrWhiteSpace((Get-EnvValue "AGENT_JPEG_QUALITY"))) {
    Set-EnvValue "AGENT_JPEG_QUALITY" "70"
  }
}

function Test-DepsReady {
  if (-not (Test-Path -LiteralPath $VenvPython)) {
    return $false
  }

@"
import importlib.util
import platform

mods = [
    "desktop_agent",
    "pyautogui",
    "mss",
    "PIL",
    "pytesseract",
    "playwright",
]
if platform.system().lower() == "windows":
    mods.append("pywinauto")
elif platform.system().lower() == "darwin":
    mods.append("ApplicationServices")
missing = [name for name in mods if importlib.util.find_spec(name) is None]
raise SystemExit(1 if missing else 0)
"@ | & $VenvPython - | Out-Null
  return $LASTEXITCODE -eq 0
}

function Invoke-PipInstall {
  param([string[]]$PipArgs)

  & $VenvPython -m pip install @PipArgs
  if ($LASTEXITCODE -eq 0) {
    return
  }
  Write-AgentLog "普通 pip 安装失败，使用 trusted-host 重试。"
  & $VenvPython -m pip install @PipArgs --trusted-host pypi.org --trusted-host files.pythonhosted.org
  if ($LASTEXITCODE -ne 0) {
    throw "pip install failed"
  }
}

function Ensure-Venv {
  if (-not (Test-Path -LiteralPath $VenvDir)) {
    Write-AgentLog "首次运行，正在创建虚拟环境..."
    Invoke-SystemPython @("-m", "venv", $VenvDir)
  }

  if (Test-DepsReady) {
    return
  }

  Write-AgentLog "正在安装/修复依赖，第一次会稍慢..."
  Invoke-PipInstall @("--upgrade", "pip")
  Invoke-PipInstall @("-e", ".[all]")
}

function Invoke-DesktopAgent {
  param([string[]]$CliArgs)
  & $VenvPython -m desktop_agent --env $EnvFile @CliArgs
}

function Bootstrap {
  Ensure-EnvFile
  Ensure-Venv
}

function Invoke-Task([string[]]$TaskParts) {
  $task = ($TaskParts -join " ").Trim()
  if ($task.Length -eq 0) {
    return
  }
  Invoke-DesktopAgent @("run", $task)
}

function Start-InteractiveLoop {
  Write-Host ""
  Write-Host "VisionDesk Agent 已准备好。"
  Write-Host "直接输入任务即可执行；输入 help 查看命令；输入 exit 退出。"
  while ($true) {
    $task = Read-Host "`n任务"
    switch -Regex ($task) {
      "^\s*$" { continue }
      "^(exit|quit|q)$" { return }
      "^(help|-help|--help)$" { Show-Help; continue }
      "^doctor$" { Invoke-DesktopAgent @("doctor"); continue }
      "^perceive$" { Invoke-DesktopAgent @("perceive", "--accessibility"); continue }
      default { Invoke-DesktopAgent @("run", $task); continue }
    }
  }
}

$Remaining = New-Object System.Collections.Generic.List[string]
$i = 0
while ($i -lt $args.Count) {
  $item = $args[$i]
  if ($item -eq "--env" -or $item -eq "-e") {
    if ($i + 1 -ge $args.Count) {
      throw "--env 需要一个文件路径"
    }
    $candidate = $args[$i + 1]
    if ([IO.Path]::IsPathRooted($candidate)) {
      $EnvFile = $candidate
    } else {
      $EnvFile = Join-Path $RootDir $candidate
    }
    $i += 2
    continue
  }
  if ($item -eq "-help" -or $item -eq "--help" -or $item -eq "help") {
    Show-Help
    exit 0
  }
  $Remaining.Add($item)
  $i += 1
}

Bootstrap

if ($Remaining.Count -eq 0) {
  Start-InteractiveLoop
  exit 0
}

$command = $Remaining[0]
$tail = @()
if ($Remaining.Count -gt 1) {
  $tail = $Remaining.GetRange(1, $Remaining.Count - 1).ToArray()
}

switch ($command) {
  "setup" {
    Write-AgentLog "环境已准备好。"
  }
  "doctor" {
    Invoke-DesktopAgent @("doctor")
  }
  "perceive" {
    if ($tail.Count -eq 0) {
      Invoke-DesktopAgent @("perceive", "--accessibility")
    } else {
      Invoke-DesktopAgent @(@("perceive") + $tail)
    }
  }
  "run" {
    Invoke-DesktopAgent @(@("run") + $tail)
  }
  "cli" {
    Invoke-DesktopAgent @tail
  }
  default {
    Invoke-Task $Remaining.ToArray()
  }
}
