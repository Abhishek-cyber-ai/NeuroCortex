# 🤖 NeuroCortex — AutoHack AI (Autonomous Hacking Assistant v5.0)

> A web-based autonomous penetration testing platform that combines a multi-agent architecture with local LLM intelligence via Ollama + MCP (Model Context Protocol). Designed for authorized security assessments — point it at a target, and let the AI agents plan, execute, and report the entire engagement.

> ⚠️ **Legal Notice:** This tool is intended **only** for use on systems you own or have **explicit written permission** to test. Unauthorized use is illegal and unethical.

---

## 📸 Overview

NeuroCortex spins up a real-time hacking dashboard in your browser — a matrix-rain terminal aesthetic with a live agent console, results panel, and a full AI chat interface. Under the hood, four specialized agents coordinate over a background task queue: Recon gathers intelligence, Exploit suggests and runs attack chains, Reporting compiles findings, and the Ollama MCP Agent lets you drive any Kali tool through natural language conversation with a local LLM.

---

## ✨ Features

### 🕸️ Multi-Agent Architecture

| Agent | Role | Key Capabilities |
|---|---|---|
| **Recon Agent** | Reconnaissance & enumeration | Network scanning, port scanning, web enumeration, DNS recon |
| **Exploit Agent** | Vulnerability exploitation | SQL injection, brute force, exploit suggestions |
| **Reporting Agent** | Findings compilation | Report generation, log analysis, finding summary |
| **Ollama MCP Agent** | AI brain + tool orchestrator | Natural language → Kali tool execution, agentic loop, all tools |

The **AgentOrchestrator** intelligently routes every command to the right agent based on keywords, with automatic fallback to target extraction and smart scanning.

---

### 🔧 Supported Kali Tools

All tool calls are routed through a `ToolManager` with an explicit allowlist and dangerous-pattern blocklist for safety:

| Tool | Purpose |
|---|---|
| `nmap` | Network & port scanning (fast / full / service detection) |
| `nikto` | Web server vulnerability scanning |
| `gobuster` | Directory and file brute-forcing |
| `hydra` | Credential brute force (SSH, FTP, HTTP, SMB) |
| `sqlmap` | Automated SQL injection testing |
| `dirb` | Web content discovery |
| `theHarvester` | OSINT / email & domain harvesting |
| `wpscan` | WordPress vulnerability scanning |
| `enum4linux` | Windows/Samba enumeration |
| `smbclient` | SMB share enumeration |
| `dnsrecon` | DNS reconnaissance |
| `whois` | Domain WHOIS lookups |
| `msfconsole` | Metasploit Framework execution |

---

### 🧠 Ollama + MCP Integration (AI Chat Tab)

The standout feature of NeuroCortex is the **AI Chat** panel — a full agentic loop powered by a locally running Ollama model and an embedded MCP server:

- Type natural language: *"Scan 10.0.0.5 and check for web vulnerabilities"*
- The AI autonomously decides which tools to call, executes them via MCP, reads the output, and loops until the task is complete
- Every tool call and result is streamed live into the chat UI with distinct visual bubbles
- Supports any Ollama model (default: `llama3.1`) — switch models from the sidebar dropdown without restarting
- Agentic loop continues calling tools until the LLM produces a final text response with no pending tool calls

The embedded MCP server exposes all supported Kali tools as structured function-call endpoints, translating Ollama tool-call JSON into real subprocess executions and returning formatted output.

---

### 🖥️ Web Dashboard

- **Matrix rain** canvas background (non-distracting, 7% opacity)
- **Two tabs:** Classic Console (command input + results panel) | AI Chat (MCP)
- **Sidebar:** Live agent status, Ollama online/offline indicator, model selector, quick-action buttons
- **Real-time updates** via Socket.IO — task completions and tool outputs pushed to the browser instantly
- **Scan modal** — select target + scan type (Quick / Full Assessment / Web) from the UI
- **Exploit modal** — auto-detect, SQL injection, or brute force with one click
- **Auto Mode** — runs a continuous recon loop every 30 seconds (toggle from sidebar)
- **Report generation** — one-click compilation of all scan findings

---

### 🛡️ Safety Controls

- **Tool allowlist** — only the 13 explicitly listed tools can be executed; anything else is rejected
- **Blocked patterns** — dangerous shell patterns (`rm -rf /`, `dd if=`, fork bombs, `mkfs`) are refused before execution
- **Timeout enforcement** — every tool call has a configured maximum runtime (60–180 seconds depending on tool)
- Tool execution never uses `shell=True`; all arguments are passed as a list

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask, Flask-SocketIO, Flask-CORS |
| AI / LLM | Ollama (local), `ollama` Python client |
| Tool Protocol | MCP (Model Context Protocol) — `mcp` Python library |
| Frontend | Vanilla JS, jQuery, Socket.IO client, CSS variables |
| Concurrency | Python `threading`, `asyncio`, background task queue |

---

## 🚀 Quick Start

### 1. Prerequisites

- **Kali Linux** (or any Debian-based distro with penetration testing tools)
- **Python 3.8+**
- **Ollama** installed and running

### 2. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve          # start the Ollama daemon
ollama pull llama3.1  # download the default model
```

### 3. Install Python Dependencies

```bash
pip install flask flask-socketio flask-cors python-socketio ollama mcp
```

### 4. Install Kali Tools (if not already present)

```bash
sudo apt update
sudo apt install nmap nikto gobuster hydra sqlmap dirb theharvester wpscan enum4linux smbclient dnsrecon whois metasploit-framework
```

### 5. Run NeuroCortex

```bash
python NeuroCortex.py
```

You will see:

```
╔═══════════════════════════════════════════════════════════════╗
║              AutoHack AI v5.0 + Ollama MCP                    ║
║         Autonomous Hacking Assistant                          ║
╠═══════════════════════════════════════════════════════════════╣
║  Web Interface : http://localhost:5000                        ║
║  Agents        : Recon | Exploit | Reporting | Ollama MCP     ║
╚═══════════════════════════════════════════════════════════════╝

    ✓ nmap
    ✓ nikto
    ✗ wpscan   ← not installed
    ...
```

### 6. Open the Interface

Navigate to `http://localhost:5000` in your browser.

---

## 💬 Usage Examples

### Classic Console Commands

```
scan 192.168.1.10               → Quick nmap + smart recon
full scan 10.0.0.5              → Full port scan with service/OS detection
nikto 192.168.1.1               → Web vulnerability scan
gobuster http://10.0.0.5        → Directory brute force
dnsrecon example.com            → DNS enumeration
exploit http://target/page?id=1 → SQL injection test
hydra brute ssh 10.0.0.5        → SSH brute force
generate report                 → Compile all findings
```

### AI Chat (MCP Tab)

```
Scan 10.0.0.1 and check for web vulnerabilities
Run a full assessment on 192.168.56.101
Check http://target.local for SQL injection
Enumerate directories on 10.10.10.5 and look for login pages
Do a DNS recon on example.com and summarize the findings
```

The AI will autonomously choose and chain tools, show every tool call and its raw output in real time, and summarize the results.

---

## 🔌 REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web dashboard |
| `GET` | `/api/tools` | List all tools and install status |
| `GET` | `/api/agents` | Agent status and metrics |
| `POST` | `/api/execute` | Run a text command through the orchestrator |
| `POST` | `/api/scan` | Queue a structured scan (`target`, `scan_type`) |
| `GET` | `/api/ollama/status` | Check Ollama availability and list models |
| `POST` | `/api/ollama/model` | Switch the active model |
| `POST` | `/api/ollama/chat` | Send a message to the AI agent |

---

## 📋 Requirements

```
flask
flask-socketio
flask-cors
python-socketio
ollama
mcp
```

---

## 👤 Author

**Abhishek Rampariya**

---

## 📄 License

This project is intended for **authorized security research and educational purposes only**. The author is not responsible for any misuse. Always obtain proper written permission before testing any system.
