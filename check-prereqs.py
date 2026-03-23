#!/usr/bin/env python3
"""
Prerequisites checker for NeGD Workshop lab repositories.

Checks all tools and dependencies required to run the three workshop labs:
  1. ghcp-pm-spec-kit              https://github.com/AkashAi7/ghcp-pm-spec-kit
  2. MCP-OS-Ticket-Lab             https://github.com/AkashAi7/MCP-OS-Ticket-Lab
  3. GuardRails-and-Secure-Coding  https://github.com/AkashAi7/GuardRails-and-Secure-Coding

Usage:
  python check-prereqs.py            # check only
  python check-prereqs.py --setup-mcp  # check + write MCP config into VS Code settings
"""

import argparse
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Counters & helpers
# ---------------------------------------------------------------------------

counts = {"pass": 0, "warn": 0, "fail": 0}

CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

# Disable colour on Windows if the terminal doesn't support ANSI
import os
if os.name == "nt":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32          # type: ignore[attr-defined]
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        CYAN = GREEN = YELLOW = RED = RESET = ""


def header(title: str) -> None:
    print()
    print(CYAN + "=" * 65 + RESET)
    print(CYAN + f"  {title}" + RESET)
    print(CYAN + "=" * 65 + RESET)


def section(title: str) -> None:
    print()
    print(YELLOW + f"  -- {title} --" + RESET)


def ok(label: str, detail: str = "") -> None:
    counts["pass"] += 1
    suffix = f"  ({detail})" if detail else ""
    print(GREEN + f"  [OK]   {label}{suffix}" + RESET)


def warn(label: str, detail: str = "") -> None:
    counts["warn"] += 1
    suffix = f"  --> {detail}" if detail else ""
    print(YELLOW + f"  [WARN] {label}{suffix}" + RESET)


def fail(label: str, hint: str = "") -> None:
    counts["fail"] += 1
    suffix = f"  --> {hint}" if hint else ""
    print(RED + f"  [FAIL] {label}{suffix}" + RESET)


def run(cmd: list[str], timeout: int = 15) -> str | None:
    """Run a command and return the first line of stdout, or None on error."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        out = result.stdout.strip() or result.stderr.strip()
        return out.splitlines()[0].strip() if out else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_git() -> None:
    section("Git")
    ver = run(["git", "--version"])
    if ver:
        ok("Git installed", ver)
    else:
        fail("Git not found", "Install from https://git-scm.com/")


def check_vscode() -> None:
    section("Visual Studio Code  [required by all labs]")
    ver = run(["code", "--version"])
    if not ver:
        fail(
            "VS Code CLI not found",
            "Install VS Code from https://code.visualstudio.com/ and add 'code' to PATH",
        )
        return
    semver = ver.splitlines()[0].strip()
    try:
        parts = semver.split(".")
        major, minor = int(parts[0]), int(parts[1])
        if major > 1 or (major == 1 and minor >= 90):
            ok(f"VS Code {semver} (>= 1.90 required)")
        else:
            warn(
                f"VS Code {semver} found",
                "Version 1.90+ is recommended - update at https://code.visualstudio.com/",
            )
    except (ValueError, IndexError):
        ok(f"VS Code installed", semver)


def check_vscode_extensions() -> None:
    section("VS Code Extensions  [required by all labs]")
    # Must capture ALL lines - run() only returns the first line
    try:
        result = subprocess.run(
            ["code", "--list-extensions"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        raw = result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        raw = ""
    if not raw:
        warn("Cannot list VS Code extensions", "Ensure the 'code' CLI is in PATH")
        return

    installed = {e.strip().lower() for e in raw.splitlines() if e.strip()}

    required = [
        ("github.copilot",      "GitHub Copilot"),
        ("github.copilot-chat", "GitHub Copilot Chat"),
    ]
    optional = [
        ("bierner.markdown-mermaid", "Markdown Preview Mermaid Support (optional - ghcp-pm-spec-kit)"),
    ]

    for ext_id, display in required:
        if ext_id in installed:
            ok(f"{display} extension installed")
        else:
            fail(
                f"{display} extension NOT installed",
                f"VS Code Extensions panel -> search '{ext_id}'",
            )

    for ext_id, display in optional:
        if ext_id in installed:
            ok(display)
        else:
            warn(display, "Optional - install via VS Code Extensions if needed")


def check_docker() -> None:
    section("Docker Desktop  [required by MCP-OS-Ticket-Lab]")

    ver = run(["docker", "--version"])
    if not ver:
        fail(
            "Docker not found",
            "Install Docker Desktop from https://www.docker.com/products/docker-desktop/",
        )
        return
    ok("Docker CLI installed", ver)

    srv = run(["docker", "info", "--format", "{{.ServerVersion}}"])
    if srv and not any(x in srv.lower() for x in ("error", "cannot", "permission")):
        ok("Docker daemon is running", f"server version {srv}")
    else:
        fail(
            "Docker daemon is NOT running",
            "Start Docker Desktop and wait until the icon is stable in the system tray",
        )

    compose_ver = run(["docker", "compose", "version", "--short"])
    if compose_ver:
        ok("Docker Compose available", compose_ver)
    else:
        fail(
            "Docker Compose not found",
            "Bundled with Docker Desktop - reinstall or update Docker Desktop",
        )


def check_python() -> None:
    section("Python 3.10+  [required by MCP-OS-Ticket-Lab]")

    major = sys.version_info.major
    minor = sys.version_info.minor
    ver_str = f"{major}.{minor}.{sys.version_info.micro}"

    if major > 3 or (major == 3 and minor >= 10):
        ok(f"Python {ver_str} installed (3.10+ required)", f"using '{sys.executable}'")
    else:
        fail(
            f"Python {ver_str} is too old (need 3.10+)",
            "Install Python 3.10+ from https://www.python.org/",
        )

    pip_ver = run([sys.executable, "-m", "pip", "--version"])
    if pip_ver:
        ok("pip available", pip_ver)
    else:
        warn("pip not found", f"Run '{sys.executable} -m ensurepip' to restore it")

    section("Required Python Packages  [MCP-OS-Ticket-Lab]")
    packages = [
        ("mcp",   "1.0.0"),
        ("httpx", "0.27.0"),
    ]
    for pkg_name, min_ver in packages:
        try:
            installed_ver = importlib.metadata.version(pkg_name)
            ok(f"Package '{pkg_name}' installed", f"version {installed_ver} (>= {min_ver} required)")
        except importlib.metadata.PackageNotFoundError:
            fail(
                f"Package '{pkg_name}' not installed",
                f"Run: pip install {pkg_name}>={min_ver}",
            )


def check_github_cli() -> None:
    section("GitHub CLI  (optional)")
    ver = run(["gh", "--version"])
    if ver:
        warn("GitHub CLI installed (optional)", ver)
    else:
        warn(
            "GitHub CLI not installed (optional)",
            "Install from https://cli.github.com/ for easier repo cloning",
        )


def check_azure_cli() -> None:
    section("Azure CLI  [required by Cloud/SRE persona - Day 2]")

    # On Windows use 'where.exe az' which resolves .cmd extensions properly;
    # shutil.which may miss az.cmd when running inside a subprocess environment.
    if os.name == "nt":
        az_loc = run(["where.exe", "az"], timeout=5)
    else:
        az_loc = shutil.which("az")

    if not az_loc:
        fail(
            "Azure CLI not found",
            "Install from https://learn.microsoft.com/cli/azure/install-azure-cli",
        )
        return
    ok("Azure CLI installed", az_loc.splitlines()[0].strip())

    # Check login status via shell=True (fully respects Windows PATH for .cmd files)
    try:
        result = subprocess.run(
            "az account show --query name -o tsv",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        account = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    except (subprocess.TimeoutExpired, OSError):
        account = ""

    if account and not any(x in account.lower() for x in ("error", "please run", "not logged")):
        ok("Azure CLI logged in", f"subscription: {account}")
    else:
        warn("Azure CLI not logged in", "Run: az login")


def _strip_jsonc_comments(text: str) -> str:
    """Strip // line comments and /* */ block comments from JSONC text."""
    # Remove block comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Remove line comments (but not URLs like https://...)
    text = re.sub(r'(?<!:)//[^\n]*', '', text)
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text


def check_vscode_mcp(setup_mcp: bool = False) -> None:
    section("VS Code MCP Server Configuration  [MCP-OS-Ticket-Lab]")

    if os.name == "nt":
        settings_path = os.path.join(os.environ.get("APPDATA", ""), "Code", "User", "settings.json")
    else:
        settings_path = os.path.expanduser("~/.config/Code/User/settings.json")

    if not os.path.isfile(settings_path):
        warn("VS Code settings.json not found", f"Expected at: {settings_path}")
        return

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            raw = f.read()
        settings: dict = json.loads(_strip_jsonc_comments(raw))
    except (json.JSONDecodeError, OSError) as exc:
        warn("Could not parse VS Code settings.json", str(exc))
        return

    mcp_servers: dict = settings.get("mcp", {}).get("servers", {})
    workshop_servers = ["osticket-mcp"]

    all_present = True
    for srv in workshop_servers:
        if srv in mcp_servers:
            ok(f"MCP server '{srv}' configured in VS Code")
        else:
            all_present = False
            warn(
                f"MCP server '{srv}' NOT configured in VS Code",
                "Run with --setup-mcp flag to auto-configure, or see README",
            )

    if not all_present and setup_mcp:
        print(CYAN + "  [INFO] Writing MCP server config to VS Code settings..." + RESET)
        try:
            settings.setdefault("mcp", {}).setdefault("servers", {})
            settings["mcp"]["servers"]["osticket-mcp"] = {
                "type": "stdio",
                "command": "python",
                "args": ["${workspaceFolder}/mcp-server/server.py"],
                "env": {
                    "OSTICKET_URL": "http://localhost:8080",
                    "OSTICKET_API_KEY": "YOUR_API_KEY_HERE",
                },
            }
            with open(settings_path, "w", encoding="utf-8") as f:
                # Write back as plain JSON (comments dropped intentionally)
                json.dump(settings, f, indent=4)
            ok("MCP server 'osticket-mcp' written to VS Code settings", settings_path)
            print(YELLOW + "  [INFO] Update OSTICKET_API_KEY in settings.json after running install-local.cmd" + RESET)
        except OSError as exc:
            fail("Failed to write MCP config", str(exc))


def check_internet() -> None:
    section("Internet / GitHub connectivity")
    try:
        req = urllib.request.Request(
            "https://github.com",
            headers={"User-Agent": "prereqs-checker/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                ok("GitHub.com is reachable")
            else:
                warn(f"GitHub returned HTTP {resp.status}")
    except urllib.error.URLError as exc:
        fail("Cannot reach github.com", f"Check network / proxy settings ({exc})")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    print()
    print(CYAN + "=" * 65 + RESET)
    print(CYAN + "  RESULT SUMMARY" + RESET)
    print(CYAN + "=" * 65 + RESET)
    print(GREEN  + f"  [OK]   Passed  : {counts['pass']}" + RESET)
    print(YELLOW + f"  [WARN] Warnings: {counts['warn']}" + RESET)
    print(RED    + f"  [FAIL] Failed  : {counts['fail']}" + RESET)
    print()
    if counts["fail"] == 0:
        print(GREEN + "  All required prerequisites are satisfied. You are ready!" + RESET)
    else:
        print(RED + "  Please fix the [FAIL] items above before starting the labs." + RESET)
    print()
    print(CYAN + "  Workshop Repositories:" + RESET)
    print("    Lab 1 (PM Spec-Kit)      : https://github.com/AkashAi7/ghcp-pm-spec-kit")
    print("    Lab 2 (MCP OS Ticket Lab): https://github.com/AkashAi7/MCP-OS-Ticket-Lab")
    print("    Lab 3 (GuardRails)       : https://github.com/AkashAi7/GuardRails-and-Secure-Coding")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="NeGD Workshop Prerequisites Checker")
    parser.add_argument(
        "--setup-mcp",
        action="store_true",
        help="Also write MCP server entries into VS Code user settings.json",
    )
    args = parser.parse_args()

    header("NeGD Workshop - Prerequisites Checker")
    print()
    print("  Checking prerequisites for all three workshop labs...")

    check_git()
    check_vscode()
    check_vscode_extensions()
    check_docker()
    check_python()
    check_azure_cli()
    check_vscode_mcp(setup_mcp=args.setup_mcp)
    check_github_cli()
    check_internet()
    print_summary()

    sys.exit(1 if counts["fail"] > 0 else 0)


if __name__ == "__main__":
    main()
