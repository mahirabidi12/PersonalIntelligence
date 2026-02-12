# Blinkit2, WhatsApp2 & AgentV1.2 - Product Requirements Document

## Original Problem Statements
1. **WhatsApp2**: Build a WhatsApp Web clone with real-time messaging
2. **Blinkit2**: Build a Blinkit grocery delivery clone
3. **AgentV1.2**: Create a browser agent (improved from V1.1) in a new folder `agentV1.2`

## Active Projects

### Blinkit2 (Running on ports 8001/3000)
- React + FastAPI + MongoDB grocery delivery clone
- 12 categories, 64+ Indian grocery products
- Cart, checkout, orders, JWT auth
- 100% tests passing

### WhatsApp2 (Previously built, preserved in /app/whatsApp2/)
- WebSocket-based real-time messaging clone
- 100% tests passing

### AgentV1.2 (Standalone project at /app/agentV1.2/)
- Browser automation agent with FastAPI dashboard
- Improvements over V1.1:
  1. Web Dashboard (HTML UI with live agent status, logs, events)
  2. WebSocket live feed for real-time log streaming
  3. General Browser Task Agent (not just WhatsApp/Blinkit)
  4. Task queue tracked in SQLite
  5. Better error recovery with MAX_RETRIES
  6. SuperMemory hot reload via API
  7. Configuration API endpoints
- Requires OpenAI API key to run
- Runs on port 8100 (separate from Blinkit2)

## AgentV1.2 Architecture
```
Orchestrator
├── WhatsApp Agent (polls messages, detects intent, auto-replies)
├── BlinkIt Agent (searches & orders groceries automatically)
├── Browser Task Agent (NEW - executes arbitrary browser tasks)
├── Event Bus (async pub/sub with WebSocket broadcast)
├── Memory (SQLite - conversations, logs, tasks, state)
├── SuperMemory (personality & guardrails from .md file)
├── Intent Detector (OpenAI LLM for chat intent + food decisions)
└── Dashboard (FastAPI + HTML UI + WebSocket live updates)
```

## Test Results
- Blinkit2 API: 100% passing
- AgentV1.2 Structure: 100% (all 17 tests passed)
- All Python files have valid syntax

## Prioritized Backlog
### P1
- Add screenshot capture system to dashboard
- Multi-tab browser support for parallel agents
- Agent execution history with replay

### P2
- Voice command support
- Scheduled task execution (cron-like)
- Plugin system for custom agents
