# Receptionist Voice Agent Demo

A real-time voice agent that acts as a dental office receptionist, built with [AssemblyAI's Voice Agent API](https://www.assemblyai.com/docs/speech-to-speech). The agent answers phone calls, checks appointment availability, books appointments, and transfers callers to a live person when needed.

## What it does

- **Answers questions** about the business — hours, location, services, insurance, providers
- **Checks appointment availability** for any date and service
- **Books appointments** by collecting patient info through natural conversation
- **Cancels appointments** by confirmation number
- **Transfers to a live person** when the caller asks or has a complex issue

## Quick start

```bash
pip install aiohttp
export ASSEMBLYAI_API_KEY="your-key-here"
python3 receptionist.py
```

Open [http://localhost:3000](http://localhost:3000) and click **Start Conversation**.

## How it works

Two files, no build step:

| File | Purpose |
|------|---------|
| `receptionist.py` | Python backend — aiohttp server, WebSocket proxy to AssemblyAI, server-side tool execution |
| `receptionist.html` | Browser frontend — AudioWorklet mic capture, PCM16 playback, dark-theme chat UI |

The browser streams mic audio to the Python server, which proxies it to AssemblyAI. When the agent wants to call a tool (check availability, book an appointment, etc.), the server intercepts the request, executes the tool, and returns the result — the browser never sees the API key.

```
Browser (mic) → WebSocket → Python proxy → AssemblyAI Voice Agent API
                                         ← agent audio + tool calls
                           Python proxy  → tool execution (server-side)
                                         → tool results back to API
```

## Customization

### Business details

Edit the `BUSINESS` dict at the top of `receptionist.py` to change the name, hours, address, services, providers, and accepted insurance.

### Real backend

The booking functions (`_create_booking`, `_check_availability`, etc.) use in-memory dicts. Replace them with your CRM or scheduling API — each function is commented with where to plug in.

### Voice

The agent uses the `claire` voice (lively, conversational). See the [AssemblyAI voice list](https://www.assemblyai.com/docs/speech-to-speech) for other options — just change the `voice` field in `session_config()`.

## Requirements

- Python 3.11+
- `aiohttp`
- An [AssemblyAI API key](https://www.assemblyai.com/dashboard)
- A modern browser with microphone access
