# AgentV1.2 — Browser Intelligence Agent

## What is this?

AgentV1.2 is an AI-powered browser automation agent that can:
- **Chat on WhatsApp** — Impersonate you in a WhatsApp conversation (using your style from SuperMemory)
- **Order on Blinkit** — Automatically order food/groceries when triggered by chat or manual command
- **Execute browser tasks** — Navigate websites, extract data, fill forms, click buttons
- **Live Dashboard** — Monitor agent status, logs, and events in real-time via web UI

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  Orchestrator                     │
│  ┌─────────┐  ┌─────────┐  ┌──────────────────┐ │
│  │WhatsApp │  │ BlinkIt │  │  Browser Task    │ │
│  │ Agent   │  │  Agent  │  │     Agent        │ │
│  └────┬────┘  └────┬────┘  └────────┬─────────┘ │
│       │            │               │             │
│  ┌────┴────────────┴───────────────┴──────────┐  │
│  │              Event Bus                      │  │
│  └────────────────────────────────────────────┘  │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │  Memory  │  │SuperMemory│  │Intent Detector│  │
│  │ (SQLite) │  │   (.md)   │  │  (LLM)       │  │
│  └──────────┘  └───────────┘  └──────────────┘  │
└──────────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │Dashboard│  ← Web UI + WebSocket live updates
    │ :8100   │
    └─────────┘
```

## Improvements over V1.1

1. **Web Dashboard** — Beautiful live monitoring UI with agent status, logs, events
2. **WebSocket Live Feed** — Real-time log streaming and event broadcasting
3. **General Browser Task Agent** — Submit arbitrary browsing tasks (not just WhatsApp/Blinkit)
4. **Task Queue** — Submit multiple tasks, tracked in SQLite
5. **Better Error Recovery** — Automatic retry with configurable MAX_RETRIES
6. **Improved Architecture** — Cleaner separation, all agents share event bus
7. **Configuration API** — View and reload config without restart
8. **SuperMemory Hot Reload** — Edit supermemory.md and reload via API

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Set your OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env

# Run
python main.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web dashboard |
| GET | `/api/status` | Agent statuses |
| GET | `/api/logs` | Activity logs |
| GET | `/api/messages` | Chat messages |
| GET | `/api/tasks` | Task history |
| GET | `/api/events` | Event log |
| GET | `/api/config` | Current config |
| GET | `/api/supermemory` | View supermemory |
| POST | `/api/task` | Submit browser task |
| POST | `/api/whatsapp/start` | Start WhatsApp agent |
| POST | `/api/order` | Trigger Blinkit order |
| POST | `/api/stop` | Stop orchestrator |
| POST | `/api/restart` | Restart orchestrator |
| POST | `/api/supermemory/reload` | Reload supermemory |
| WS | `/ws` | Live event stream |

## File Structure

```
agentV1.2/
├── main.py                 # Entry point (FastAPI + WebSocket)
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── supermemory.md          # Personality & guardrails
├── agents/
│   ├── base_agent.py       # Abstract base
│   ├── whatsapp_agent.py   # WhatsApp chat agent
│   ├── blinkit_agent.py    # Blinkit ordering agent
│   └── browser_agent.py    # General browser task agent (NEW)
├── core/
│   ├── orchestrator.py     # Central controller
│   ├── memory.py           # SQLite memory
│   ├── intent.py           # LLM intent detection
│   └── supermemory.py      # Personality loader
├── events/
│   └── bus.py              # Async event bus
├── models/
│   └── schemas.py          # Pydantic models
├── prompts/
│   ├── girlfriend.py       # Chat prompt builder
│   ├── decision.py         # Food selection prompt
│   └── intent.py           # Intent classification prompt
├── ui/
│   └── dashboard.html      # Web dashboard
└── data/
    └── memory.db           # SQLite database (auto-created)
```
