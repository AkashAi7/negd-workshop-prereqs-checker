# NeGD Workshop — Prerequisites Checker

Automated prerequisite checker for the three NeGD × GitHub Copilot workshop labs.
Run it **before the workshop** to ensure your machine has everything installed and configured.

## Workshop Labs Covered

| Lab | Repository |
|-----|-----------|
| Lab 1 — GitHub Copilot PM Spec-Kit | [AkashAi7/ghcp-pm-spec-kit](https://github.com/AkashAi7/ghcp-pm-spec-kit) |
| Lab 2 — MCP OS Ticket Lab | [AkashAi7/MCP-OS-Ticket-Lab](https://github.com/AkashAi7/MCP-OS-Ticket-Lab) |
| Lab 3 — GuardRails and Secure Coding | [AkashAi7/GuardRails-and-Secure-Coding](https://github.com/AkashAi7/GuardRails-and-Secure-Coding) |

## What Gets Checked

| Check | Required By |
|-------|-------------|
| Git | All labs |
| VS Code 1.90+ (with `code` CLI in PATH) | All labs |
| GitHub Copilot extension | All labs |
| GitHub Copilot Chat extension | All labs |
| Markdown Preview Mermaid Support | Lab 1 (optional) |
| Docker Desktop + daemon running | Lab 2 |
| Docker Compose | Lab 2 |
| Python 3.10+ | Lab 2 |
| pip | Lab 2 |
| `mcp >= 1.0.0` Python package | Lab 2 |
| `httpx >= 0.27.0` Python package | Lab 2 |
| Azure CLI + login status | Lab 3 (Day 2 Cloud/SRE persona) |
| VS Code MCP server config (`osticket-mcp`) | Lab 2 |
| GitHub CLI | All labs (optional) |
| Internet / GitHub connectivity | All labs |

Results are colour-coded:
- `[OK]` — requirement met
- `[WARN]` — optional or advisory
- `[FAIL]` — must fix before starting the lab

---

## Option A — PowerShell (Windows)

### Prerequisites
- Windows PowerShell 5.1+ or PowerShell 7+

### Run (check only)

```powershell
.\check-prereqs.ps1
```

### Run (check + auto-configure MCP server in VS Code)

```powershell
.\check-prereqs.ps1 -SetupMCP
```

> **Note:** If you get a script execution policy error, run:
> ```powershell
> powershell -ExecutionPolicy Bypass -File .\check-prereqs.ps1
> ```

---

## Option B — Python (Windows / macOS / Linux)

### Prerequisites
- Python 3.10+ (no extra packages needed — stdlib only)

### Run (check only)

```bash
python check-prereqs.py
```

### Run (check + auto-configure MCP server in VS Code)

```bash
python check-prereqs.py --setup-mcp
```

---

## What `-SetupMCP` / `--setup-mcp` Does

When this flag is passed and the `osticket-mcp` server is not yet configured, the
script writes the following entry into your VS Code **user** `settings.json`
automatically:

```json
"mcp": {
  "servers": {
    "osticket-mcp": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/mcp-server/server.py"],
      "env": {
        "OSTICKET_URL": "http://localhost:8080",
        "OSTICKET_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

After running `install-local.cmd` (Lab 2 setup), replace `YOUR_API_KEY_HERE`
with the API key from the osTicket admin panel
(`Admin Panel > API > API Keys`).

---

## Fixing Common Issues

| Issue | Fix |
|-------|-----|
| `VS Code CLI not found` | In VS Code: `Ctrl+Shift+P` → **Shell Command: Install 'code' command in PATH** |
| `GitHub Copilot extension NOT installed` | VS Code Extensions panel → search `GitHub.Copilot` → Install |
| `Docker daemon is NOT running` | Start Docker Desktop and wait for the whale icon to stabilise |
| `Azure CLI not found` | [Install Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| `Azure CLI not logged in` | Run `az login` in your terminal |
| `Package 'mcp' not installed` | Run `pip install mcp>=1.0.0 httpx>=0.27.0` |

---

*NeGD x GitHub Copilot Workshop*
