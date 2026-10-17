# MyJarvis — Personal AI Assistant Daemon

**ALFRED personality • Windows-native • Always-on • API-only (NVIDIA nemotron-3-ultra)**

---

## 🚀 Quick Start

```bash
# 1. Clone / download
cd C:\Users\herog\MyJarvis

# 2. Run installer (as Administrator for auto-start)
install.bat

# 3. Edit config with your API key
notepad %USERPROFILE%\.myjarvis\config.toml

# 4. Test
myjarvis ask "Olá, Jarvis"

# 5. Run daemon (background)
myjarvis-daemon

# Or with system tray icon
myjarvis-tray
```

---

## ⚙️ Configuration

Edit `~/.myjarvis/config.toml`:

```toml
[intelligence]
# NVIDIA API (OpenAI-compatible)
engine_config = { provider = "openai", base_url = "https://integrate.api.nvidia.com/v1", api_key = "SUA_CHAVE_AQUI" }
default_model = "nvidia/nemotron-3-ultra-550b-a55b"
temperature = 0.3
max_tokens = 4096

[daemon]
auto_start = true
tray_icon = true
ipc_port = 8765  # Para integração com ALFRED/Hermes

[skills]
enabled = [
    "windows_control",  # Apps, janelas, volume, power
    "bluetooth",        # Scan, connect, battery
    "audio",            # Volume, devices, recording
    "filesystem",       # Search, read, write, watch
    "process",          # List, kill, monitor
    "network",          # Ping, speedtest, DNS
    "power",            # Sleep, hibernate, battery
    "schedule",         # Cron, timers, reminders
    "clipboard",        # History, monitor
    "screenshot",       # Capture + OCR
]
```

---

## 🎯 Usage

### CLI
```bash
# Single question
myjarvis ask "Qual a capital da França?"

# Streaming
myjarvis ask "Explique quantum computing" --stream

# Interactive chat
myjarvis chat

# Memory
myjarvis memory index "C:\Projetos"
myjarvis memory search "configuração redis"

# Skills
myjarvis skill windows_control volume 50
myjarvis skill bluetooth scan
myjarvis skill screenshot capture
```

### Daemon (Always-on)
```bash
# Background daemon
myjarvis-daemon

# With system tray (recommended)
myjarvis-tray
```

### IPC Bridge (ALFRED/Hermes Integration)
WebSocket em `ws://127.0.0.1:8765`:

```json
// Ask
{"id": "1", "type": "ask", "payload": {"query": "Como está o sistema?"}}

// Skill
{"id": "2", "type": "skill", "payload": {"skill": "process", "action": "list", "kwargs": {}}}

// Status
{"id": "3", "type": "status", "payload": {}}
```

---

## 🧠 ALFRED Personality

> Mordomo britânico sofisticado, irônico, tecnicamente competente.
> Direto, sem filler, concorda quando faz sentido.
> PT-BR nativo, palavrões contextuais.

---

## 📁 Structure

```
~/.myjarvis/
├── config.toml           # Configuração principal
├── SOUL.md               # Personalidade (auto-gerado)
├── MEMORY.md             # Fatos persistentes
├── USER.md               # Perfil do usuário
├── memory.db             # SQLite (memória + embeddings)
├── telemetry.db          # Métricas
├── logs/
│   └── myjarvis.log
├── skills/               # Skills customizadas
└── cache/
```

---

## 🛠️ Skills Incluídas

| Skill | Ações |
|-------|-------|
| `windows_control` | launch, close, focus, volume, brightness, power, shortcut, startup |
| `bluetooth` | scan, list, connect, disconnect, pair, unpair, battery, audio |
| `audio` | volume, mute, devices, record, play, format |
| `filesystem` | search, read, write, copy, move, delete, watch, hash |
| `process` | list, kill, info, cpu, memory, tree, priority |
| `network` | ping, speedtest, interfaces, connections, dns, traceroute, port |
| `power` | sleep, hibernate, shutdown, restart, lock, battery, plan |
| `schedule` | cron, timer, reminder, list, enable/disable, run_now |
| `clipboard` | get, set, history, clear, monitor, paste |
| `screenshot` | capture (screen/window/region), ocr |

---

## 🔧 Development

```bash
# Install dev deps
pip install -e ".[dev]"

# Run tests
pytest tests/

# Lint
ruff check myjarvis/
mypy myjarvis/
```

---

## 📦 Uninstall

```bash
myjarvis-setup --uninstall
# Or manually:
pip uninstall myjarvis
schtasks /delete /tn "MyJarvis" /f
rmdir /s %USERPROFILE%\.myjarvis
```

---

## 📄 License

MIT — Use freely, modify, distribute.

---

**Built with:** OpenJarvis core + custom NVIDIA engine + Windows skills + ALFRED soul.