#Requires -Version 5.1
<#
.SYNOPSIS
    Prerequisites checker for NeGD Workshop lab repositories.
.DESCRIPTION
    Checks all tools and dependencies required to run the three workshop labs:
      1. ghcp-pm-spec-kit           https://github.com/AkashAi7/ghcp-pm-spec-kit
      2. MCP-OS-Ticket-Lab          https://github.com/AkashAi7/MCP-OS-Ticket-Lab
      3. GuardRails-and-Secure-Coding  https://github.com/AkashAi7/GuardRails-and-Secure-Coding
#>

$script:passCount = 0
$script:warnCount = 0
$script:failCount = 0

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 65) -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host ("=" * 65) -ForegroundColor Cyan
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "  -- $Title --" -ForegroundColor Yellow
}

function Pass {
    param([string]$Label, [string]$Detail = "")
    $script:passCount++
    if ($Detail) {
        Write-Host "  [OK]   $Label  ($Detail)" -ForegroundColor Green
    } else {
        Write-Host "  [OK]   $Label" -ForegroundColor Green
    }
}

function Warn {
    param([string]$Label, [string]$Detail = "")
    $script:warnCount++
    if ($Detail) {
        Write-Host "  [WARN] $Label  --> $Detail" -ForegroundColor Yellow
    } else {
        Write-Host "  [WARN] $Label" -ForegroundColor Yellow
    }
}

function Fail {
    param([string]$Label, [string]$Hint = "")
    $script:failCount++
    if ($Hint) {
        Write-Host "  [FAIL] $Label  --> $Hint" -ForegroundColor Red
    } else {
        Write-Host "  [FAIL] $Label" -ForegroundColor Red
    }
}

function Install-WingetDependency {
    param([string]$WingetId, [string]$Name)
    Write-Host "  [INFO] Attempting to install $Name via winget..." -ForegroundColor Cyan
    try {
        $null = & winget install --id $WingetId -e --source winget --accept-package-agreements --accept-source-agreements
        Write-Host "  [INFO] Installed $Name. You may need to restart your terminal for it to be available in PATH." -ForegroundColor Cyan
    } catch {
        Fail "$Name installation failed" "Please install manually."
    }
}

function Get-CmdOutput {
    param([string]$Cmd, [string[]]$CmdArgs)
    try {
        $out = & $Cmd @CmdArgs 2>&1 | Select-Object -First 1
        return $out.ToString().Trim()
    } catch {
        return $null
    }
}

# -------------------------------------------------------------------------
# Individual checks
# -------------------------------------------------------------------------

function Test-Git {
    Write-Section "Git"
    $ver = Get-CmdOutput git @("--version")
    if ($ver) {
        Pass "Git installed" $ver
    } else {
        Warn "Git not found" "Attempting to install..."
        Install-WingetDependency -WingetId "Git.Git" -Name "Git"
    }
}

function Test-VSCode {
    Write-Section "Visual Studio Code  [required by all labs]"
    $ver = Get-CmdOutput code @("--version")
    if (-not $ver) {
        Warn "VS Code CLI not found" "Attempting to install..."
        Install-WingetDependency -WingetId "Microsoft.VisualStudioCode" -Name "VS Code"
        return
    }
    $semver = ($ver -split "`n")[0].Trim()
    $parts  = $semver -split "\."
    $major  = [int]$parts[0]
    $minor  = [int]$parts[1]
    if ($major -gt 1 -or ($major -eq 1 -and $minor -ge 90)) {
        Pass "VS Code $semver (>= 1.90 required)"
    } else {
        Warn "VS Code $semver found" "Version 1.90+ is recommended - update at https://code.visualstudio.com/"
    }
}

function Test-VSCodeExtensions {
    Write-Section "VS Code Extensions  [required by all labs]"
    # Must capture ALL lines - Get-CmdOutput only returns the first line
    try {
        $rawList = & code --list-extensions 2>&1
    } catch {
        $rawList = $null
    }
    if (-not $rawList) {
        Warn "Cannot list VS Code extensions" "Ensure the 'code' CLI is in PATH"
        return
    }
    $extList = $rawList | ForEach-Object { $_.ToString().Trim().ToLower() } | Where-Object { $_ -ne '' }

    $required = @(
        [PSCustomObject]@{ Id = "github.copilot";      Display = "GitHub Copilot" },
        [PSCustomObject]@{ Id = "github.copilot-chat"; Display = "GitHub Copilot Chat" }
    )
    $optional = @(
        [PSCustomObject]@{ Id = "bierner.markdown-mermaid"; Display = "Markdown Preview Mermaid Support (optional - ghcp-pm-spec-kit)" }
    )

    foreach ($ext in $required) {
        if ($extList -contains $ext.Id) {
            Pass "$($ext.Display) extension installed"
        } else {
            Warn "$($ext.Display) extension NOT installed" "Attempting to install..."
            & code --install-extension $ext.Id | Out-Null
            Pass "$($ext.Display) extension installed"
        }
    }
    foreach ($ext in $optional) {
        if ($extList -contains $ext.Id) {
            Pass "$($ext.Display)"
        } else {
            Warn "$($ext.Display)" "Attempting to install optional extension..."
            & code --install-extension $ext.Id | Out-Null
            Pass "$($ext.Display) extension installed"
        }
    }
}

function Test-Docker {
    Write-Section "Docker Desktop  [required by MCP-OS-Ticket-Lab]"
    $ver = Get-CmdOutput docker @("--version")
    if (-not $ver) {
        Warn "Docker not found" "Attempting to install..."
        Install-WingetDependency -WingetId "Docker.DockerDesktop" -Name "Docker Desktop"
        return
    }
    Pass "Docker CLI installed" $ver

    $srvVer = Get-CmdOutput docker @("info", "--format", "{{.ServerVersion}}")
    if ($srvVer -and $srvVer -notmatch "error|cannot|permission|Cannot") {
        Pass "Docker daemon is running" "server version $srvVer"
    } else {
        Fail "Docker daemon is NOT running" "Start Docker Desktop and wait until the icon is stable in the system tray"
    }

    $composeVer = Get-CmdOutput docker @("compose", "version", "--short")
    if ($composeVer) {
        Pass "Docker Compose available" $composeVer
    } else {
        Fail "Docker Compose not found" "Bundled with Docker Desktop - reinstall or update Docker Desktop"
    }
}

function Test-Python {
    Write-Section "Python 3.10+  [required by MCP-OS-Ticket-Lab]"

    $pythonCmd = $null
    foreach ($cmd in @("python", "python3")) {
        $v = Get-CmdOutput $cmd @("--version")
        if ($v -and $v -match "Python (\d+)\.(\d+)") {
            $pythonCmd = $cmd
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            $verStr = "$($major).$($minor)"
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                Pass "Python $verStr installed (3.10+ required)" "using '$cmd'"
            } else {
                Fail "Python $verStr is too old (need 3.10+)" "Install Python 3.10+ from https://www.python.org/"
            }
            break
        }
    }
    if (-not $pythonCmd) {
        Warn "Python not found" "Attempting to install Python 3.12..."
        Install-WingetDependency -WingetId "Python.Python.3.12" -Name "Python"
        return
    }

    $pip = Get-CmdOutput pip @("--version")
    if (-not $pip) { $pip = Get-CmdOutput pip3 @("--version") }
    if ($pip) {
        Pass "pip available" $pip
    } else {
        Warn "pip not found" "Attempting to restore pip..."
        & $pythonCmd -m ensurepip | Out-Null
    }

    Write-Section "Required Python Packages  [MCP-OS-Ticket-Lab]"
    $packages = @(
        [PSCustomObject]@{ Name = "mcp";   MinVer = "1.0.0"  },
        [PSCustomObject]@{ Name = "httpx"; MinVer = "0.27.0" }
    )
    foreach ($pkg in $packages) {
        $pkgName = $pkg.Name
        $pyCode = "import importlib.metadata; print(importlib.metadata.version('$pkgName'))"
        $result = & $pythonCmd -c $pyCode 2>&1 | Select-Object -First 1
        if ($result) { $result = $result.ToString().Trim() }
        if ($result -and $result -notmatch "PackageNotFoundError|No module") {
            Pass "Package '$pkgName' installed" "version $result (>= $($pkg.MinVer) required)"
        } else {
            Warn "Package '$pkgName' not installed" "Attempting to install via pip..."
            & $pythonCmd -m pip install "$pkgName>=$($pkg.MinVer)" | Out-Null
            Pass "Package '$pkgName' installed"
        }
    }
}

function Test-AzureCLI {
    Write-Section "Azure CLI  [required by Cloud/SRE persona - Day 2]"

    # Fast PATH existence check before running the (slow) az --version
    $azCmd = Get-Command az -ErrorAction SilentlyContinue
    if (-not $azCmd) {
        Warn "Azure CLI not found" "Attempting to install..."
        Install-WingetDependency -WingetId "Microsoft.AzureCLI" -Name "Azure CLI"
        return
    }

    # az.cmd can be slow on first load - run in a job with a generous timeout
    $job = Start-Job -ScriptBlock { & az --version 2>&1 | Select-Object -First 1 }
    $null = Wait-Job $job -Timeout 30
    $ver = Receive-Job $job
    Remove-Job $job -Force

    if ($ver) {
        Pass "Azure CLI installed" $ver
    } else {
        Warn "Azure CLI found but did not respond in time" "Try running 'az --version' manually"
        return
    }

    # Check login status
    $accountJob = Start-Job -ScriptBlock { & az account show --query name -o tsv 2>&1 | Select-Object -First 1 }
    $null = Wait-Job $accountJob -Timeout 30
    $account = Receive-Job $accountJob
    Remove-Job $accountJob -Force

    if ($account -and $account -notmatch "error|Please run|not logged|az login") {
        Pass "Azure CLI logged in" "subscription: $account"
    } else {
        Warn "Azure CLI not logged in" "Run: az login"
    }
}


function Test-GitHubCLI {
    Write-Section "GitHub CLI  (optional)"
    $ver = Get-CmdOutput gh @("--version")
    if ($ver) {
        Warn "GitHub CLI installed (optional)" $ver
    } else {
        Warn "GitHub CLI not installed (optional)" "Attempting to install..."
        Install-WingetDependency -WingetId "GitHub.cli" -Name "GitHub CLI"
    }
}

function Test-InternetAccess {
    Write-Section "Internet / GitHub connectivity"
    try {
        $resp = Invoke-WebRequest -Uri "https://github.com" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Pass "GitHub.com is reachable"
        } else {
            Warn "GitHub returned HTTP $($resp.StatusCode)"
        }
    } catch {
        Fail "Cannot reach github.com" "Check network connection and/or corporate proxy settings"
    }
}

# -------------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------------

function Write-Summary {
    Write-Host ""
    Write-Host ("=" * 65) -ForegroundColor Cyan
    Write-Host "  RESULT SUMMARY" -ForegroundColor Cyan
    Write-Host ("=" * 65) -ForegroundColor Cyan
    Write-Host "  [OK]   Passed  : $script:passCount" -ForegroundColor Green
    Write-Host "  [WARN] Warnings: $script:warnCount" -ForegroundColor Yellow
    Write-Host "  [FAIL] Failed  : $script:failCount" -ForegroundColor Red
    Write-Host ""
    if ($script:failCount -eq 0) {
        Write-Host "  All required prerequisites are satisfied. You are ready!" -ForegroundColor Green
    } else {
        Write-Host "  Please fix the [FAIL] items above before starting the labs." -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "  Workshop Repositories:" -ForegroundColor Cyan
    Write-Host "    Lab 1 (PM Spec-Kit)      : https://github.com/AkashAi7/ghcp-pm-spec-kit"
    Write-Host "    Lab 2 (MCP OS Ticket Lab): https://github.com/AkashAi7/MCP-OS-Ticket-Lab"
    Write-Host "    Lab 3 (GuardRails)       : https://github.com/AkashAi7/GuardRails-and-Secure-Coding"
    Write-Host ""
}

# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

Write-Header "NeGD Workshop - Prerequisites Checker"
Write-Host ""
Write-Host "  Checking prerequisites for all three workshop labs..."

Test-Git
Test-VSCode
Test-VSCodeExtensions
Test-Docker
Test-Python
Test-AzureCLI
Test-GitHubCLI
Test-InternetAccess
Write-Summary