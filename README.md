# Receptionist Voice Agent Demo

A real-time voice agent that acts as a business receptionist, built with [AssemblyAI's Voice Agent API](https://www.assemblyai.com/docs/voice-agents/speech-to-speech). Walk through a guided setup, configure your business, pick a voice, and start talking — all in the browser.

**This is a demo.** Appointments, availability, and call transfers are all simulated with in-memory data. Nothing connects to a real calendar, CRM, or phone system. It's designed to show what a production receptionist agent could look and feel like.

## Quick start

```bash
pip install aiohttp
export ASSEMBLYAI_API_KEY="your-key-here"
python3 receptionist.py
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Onboarding flow

When you open the app, you walk through a 4-step setup:

1. **Pick a voice** — 18 voice cards to choose from (Dawn is the default)
2. **Business details** — name, receptionist name, phone, address, and hours
3. **Services & providers** — add/edit/remove services, providers, and insurance plans
4. **Review & launch** — see a summary of your config, view the appointment calendar, and hit Launch

Each step animates in with a progress bar at the top. Everything auto-saves to `config.json` as you edit — no save button needed.

## During a call

Once you launch, the app switches to a call screen with:

- Live transcript — your words and the agent's responses as chat bubbles
- Status indicator — Connecting, Ready, Listening, Speaking
- Tool activity — shows when the agent is looking something up or booking
- **End Call** — disconnects and takes you back to the review screen
- **Settings** — goes back to step 1 so you can reconfigure

## What's simulated (not real)

This is a self-contained demo — all backend logic runs in-memory with no external integrations:

| Feature | What it does in the demo | What you'd replace it with |
|---------|-------------------------|---------------------------|
| **Availability** | Randomly generates open slots for any date | Your scheduling system API (Calendly, Acuity, etc.) |
| **Booking** | Stores appointments in a Python dict, gone on restart | Your CRM or database (Salesforce, HubSpot, etc.) |
| **Cancellation** | Removes from the in-memory dict | Your scheduling system API |
| **Business info** | Reads from `config.json` on disk | Your CMS or database |
| **Call transfer** | Returns a "transferring" message, doesn't actually transfer | Your telephony system (Twilio, etc.) |

Each tool function in `receptionist.py` is commented with where to plug in real API calls — search for `Replace with` in the code.

## How it works

Two files, no build step:

| File | Purpose |
|------|---------|
| `receptionist.py` | Python backend — aiohttp server, WebSocket proxy to AssemblyAI, server-side tool execution, config REST API |
| `receptionist.html` | Browser frontend — onboarding UI, voice picker, calendar, AudioWorklet mic capture, chat UI |

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
