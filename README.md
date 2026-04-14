# Receptionist Voice Agent Demo

A real-time voice agent that acts as a business receptionist, built with [AssemblyAI's Voice Agent API](https://www.assemblyai.com/docs/voice-agents/speech-to-speech). The agent answers phone calls, checks appointment availability, books appointments, and transfers callers to a live person when needed.

Includes a full interactive configuration UI — pick a voice, edit business details, manage services, and view booked appointments on a calendar. All changes save locally and persist across restarts.

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

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Interactive configuration

The left sidebar lets you customize everything without touching code:

| Section | What you can change |
|---------|-------------------|
| **Voice** | Pick from 18 voices — click a card to switch |
| **Business** | Name, receptionist name, phone, address |
| **Hours** | Set hours for each day of the week |
| **Services** | Add, edit, or remove services with duration and price |
| **Providers** | Manage the provider list |
| **Insurance** | Manage accepted insurance plans |
| **Appointments** | Monthly calendar showing booked appointments |

Changes save to `config.json` automatically and take effect on the next conversation.

## How it works

Two files, no build step:

| File | Purpose |
|------|---------|
| `receptionist.py` | Python backend — aiohttp server, WebSocket proxy, tool execution, config REST API |
| `receptionist.html` | Browser frontend — config sidebar, voice picker, calendar, AudioWorklet capture, chat UI |

```
Browser (config) → POST /api/config → saves to config.json
Browser (mic)    → WebSocket → Python proxy → AssemblyAI Voice Agent API
                                            ← agent audio + tool calls
                              Python proxy  → tool execution (server-side)
                                            → tool results back to API
```

The browser never sees the API key. Tool execution and config persistence are entirely server-side.

## Requirements

- Python 3.11+
- `aiohttp`
- An [AssemblyAI API key](https://www.assemblyai.com/dashboard)
- A modern browser with microphone access
