import asyncio
import base64
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from aiohttp import web, ClientSession, WSMsgType

API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "<your-api-key>")
AAI_URL = "wss://agents.assemblyai.com/v1/realtime"
PORT = int(os.environ.get("PORT", 3000))

# ---------------------------------------------------------------------------
# 1. Domain data — replace with real database / CRM calls
# ---------------------------------------------------------------------------

BUSINESS = {
    "name": "Bright Smile Dental",
    "phone": "555-123-4567",
    "address": "742 Evergreen Terrace, Suite 200, Springfield",
    "hours": {
        "Monday": "8:00 AM – 5:00 PM",
        "Tuesday": "8:00 AM – 5:00 PM",
        "Wednesday": "8:00 AM – 5:00 PM",
        "Thursday": "8:00 AM – 6:00 PM",
        "Friday": "8:00 AM – 3:00 PM",
        "Saturday": "9:00 AM – 1:00 PM",
        "Sunday": "Closed",
    },
    "services": [
        {"name": "Cleaning", "duration": 60, "price": 150},
        {"name": "Teeth Whitening", "duration": 90, "price": 350},
        {"name": "Filling", "duration": 45, "price": 200},
        {"name": "Crown", "duration": 90, "price": 800},
        {"name": "Root Canal", "duration": 120, "price": 1200},
        {"name": "Consultation", "duration": 30, "price": 0},
    ],
    "providers": ["Dr. Patel", "Dr. Kim", "Dr. Rodriguez"],
    "insurance_accepted": [
        "Delta Dental", "Cigna", "Aetna", "MetLife", "Guardian",
    ],
}

# In-memory appointment store — replace with a real database
BOOKINGS: dict[str, dict] = {}


def _get_business_info(topic: str) -> dict:
    """Return business info filtered by topic."""
    topic = topic.lower()
    if "hour" in topic or "open" in topic or "close" in topic:
        return {"hours": BUSINESS["hours"]}
    if "address" in topic or "location" in topic or "direction" in topic:
        return {"address": BUSINESS["address"]}
    if "service" in topic or "offer" in topic or "procedure" in topic:
        return {"services": BUSINESS["services"]}
    if "insurance" in topic or "accept" in topic or "plan" in topic:
        return {"insurance_accepted": BUSINESS["insurance_accepted"]}
    if "provider" in topic or "doctor" in topic or "dentist" in topic:
        return {"providers": BUSINESS["providers"]}
    if "phone" in topic or "contact" in topic or "number" in topic:
        return {"phone": BUSINESS["phone"], "address": BUSINESS["address"]}
    # General info
    return {
        "name": BUSINESS["name"],
        "phone": BUSINESS["phone"],
        "address": BUSINESS["address"],
        "hours_today": BUSINESS["hours"].get(
            datetime.now().strftime("%A"), "Closed"
        ),
    }


def _check_availability(args: dict) -> dict:
    """Simulate checking available slots for a date + optional service."""
    date_str = args.get("date", "tomorrow")
    service = args.get("service", "")

    # Generate fake available slots
    slots = []
    for hour in [9, 10, 11, 13, 14, 15, 16]:
        if random.random() > 0.35:  # ~65 % chance each slot is open
            slots.append(f"{hour}:00")
    if not slots:
        slots = ["10:00", "14:00"]  # always at least two

    providers_available = random.sample(
        BUSINESS["providers"], k=random.randint(1, len(BUSINESS["providers"]))
    )
    return {
        "date": date_str,
        "service": service or "any",
        "available_slots": slots,
        "providers": providers_available,
    }


def _book_appointment(args: dict) -> dict:
    """Create a booking. Replace with your CRM / scheduling API."""
    conf = f"BK-{uuid.uuid4().hex[:6].upper()}"
    booking = {
        "confirmation": conf,
        "status": "confirmed",
        "patient_name": args.get("patient_name", ""),
        "date": args.get("date", ""),
        "time": args.get("time", ""),
        "service": args.get("service", ""),
        "provider": args.get("provider", ""),
        "phone": args.get("phone", ""),
    }
    BOOKINGS[conf] = booking
    return booking


def _cancel_appointment(args: dict) -> dict:
    """Cancel a booking by confirmation number."""
    conf = args.get("confirmation_number", "").upper()
    if conf in BOOKINGS:
        BOOKINGS[conf]["status"] = "cancelled"
        return {"confirmation": conf, "status": "cancelled"}
    return {"error": f"Booking {conf} not found"}


def _transfer_call(args: dict) -> dict:
    """Simulate transferring the call to a live person."""
    reason = args.get("reason", "general inquiry")
    department = args.get("department", "front desk")
    return {
        "status": "transferring",
        "department": department,
        "reason": reason,
        "message": f"Transferring to {department}. Please hold.",
    }


# ---------------------------------------------------------------------------
# 2. Tool definitions (JSON Schema for the LLM)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "name": "get_business_info",
        "description": (
            "Look up information about the business such as hours, location, "
            "services offered, insurance accepted, providers, or contact info. "
            "Call this whenever someone asks a question about the practice."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": (
                        "What the caller is asking about: hours, location, "
                        "services, insurance, providers, or contact"
                    ),
                },
            },
            "required": ["topic"],
        },
    },
    {
        "type": "function",
        "name": "check_availability",
        "description": (
            "Check available appointment slots for a given date and optional "
            "service. Call this when someone asks about openings or wants to "
            "know when they can come in."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to check, e.g. 'tomorrow', 'next Monday', '2026-04-20'",
                },
                "service": {
                    "type": "string",
                    "description": "Service type if specified, e.g. 'cleaning', 'filling'",
                },
            },
            "required": ["date"],
        },
    },
    {
        "type": "function",
        "name": "book_appointment",
        "description": (
            "Book an appointment once the caller has confirmed a date, time, "
            "and service. Collect the patient's name and phone number before "
            "calling this."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Full name of the patient",
                },
                "date": {"type": "string", "description": "Appointment date"},
                "time": {"type": "string", "description": "Appointment time"},
                "service": {"type": "string", "description": "Service booked"},
                "provider": {
                    "type": "string",
                    "description": "Preferred provider if any",
                },
                "phone": {
                    "type": "string",
                    "description": "Patient callback phone number",
                },
            },
            "required": ["patient_name", "date", "time", "service"],
        },
    },
    {
        "type": "function",
        "name": "cancel_appointment",
        "description": (
            "Cancel an existing appointment by confirmation number."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "confirmation_number": {
                    "type": "string",
                    "description": "The booking confirmation code, e.g. BK-A3F219",
                },
            },
            "required": ["confirmation_number"],
        },
    },
    {
        "type": "function",
        "name": "transfer_call",
        "description": (
            "Transfer the caller to a live team member. Use when the caller "
            "explicitly asks to speak with a person, has a complex issue you "
            "can't resolve, or is upset."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Brief reason for the transfer",
                },
                "department": {
                    "type": "string",
                    "description": "Department to transfer to: front desk, billing, or provider",
                },
            },
            "required": ["reason"],
        },
    },
]

# ---------------------------------------------------------------------------
# 3. Tool execution
# ---------------------------------------------------------------------------


async def execute_tool(event: dict) -> dict:
    name = event.get("name", "")
    args = event.get("args", {})

    if name == "get_business_info":
        result = _get_business_info(args)
    elif name == "check_availability":
        result = _check_availability(args)
    elif name == "book_appointment":
        result = _book_appointment(args)
    elif name == "cancel_appointment":
        result = _cancel_appointment(args)
    elif name == "transfer_call":
        result = _transfer_call(args)
    else:
        result = {"error": f"Unknown tool: {name}"}

    return {"call_id": event.get("call_id", ""), "result": result}


# ---------------------------------------------------------------------------
# 4. Session configuration
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""\
You are the receptionist at {BUSINESS['name']}. Your name is Claire. You answer \
the phone, help callers with questions, check appointment availability, book \
appointments, and transfer calls when needed.

Speech style:
- Keep every response to one or two short sentences. This is a phone call, not an essay.
- Sound warm and natural. Use brief filler words like "one sec" or "let me check" before \
tool calls. Never narrate what you're about to do.
- Do not use exclamation points. Stay calm and friendly.
- Never say "Certainly", "Absolutely", "Of course!", or "I'd be happy to."
- When reading back a confirmation number, say each character slowly with the NATO phonetic \
alphabet, e.g. "B as in Bravo, K as in Kilo, dash, A 3 F 2 1 9."

Responsibilities:
1. Answer questions about the business — hours, location, services, insurance, providers. \
When someone asks, say "Let me look that up" and call get_business_info. Then relay the \
answer conversationally in one or two sentences.

2. Check appointment availability — when someone wants to come in, ask what service they \
need and when, then say "One sec" and call check_availability. Offer two or three of the \
available times, not the full list.

3. Book appointments — collect the patient's name, preferred date/time, and service through \
natural conversation (not as a checklist). Ask for a callback number. Once you have \
everything, say "Let me get that booked" and call book_appointment. Read back the \
confirmation number slowly.

4. Cancel appointments — ask for the confirmation number, then say "One moment" and call \
cancel_appointment.

5. Transfer calls — if the caller asks to speak with someone, has a billing question you \
can't answer, or is upset, say "Let me connect you" and call transfer_call. Don't try to \
handle things outside your scope.

Important:
- Never announce a tool call. Just use a short filler and call the tool.
- After getting a tool result, give the answer directly. Don't say "According to our system" \
or "I found that."
- If a caller asks something you don't know, offer to transfer them.
- Collect info naturally through conversation. Don't list fields.
"""

GREETING = f"Hi, {BUSINESS['name']}, this is Claire. How can I help you?"


def session_config() -> dict:
    return {
        "type": "session.update",
        "session": {
            "voice": "claire",
            "system_prompt": SYSTEM_PROMPT,
            "greeting": GREETING,
            "tools": TOOLS,
            "turn_detection": {
                "max_turn_silence_ms": 1000,
                "min_end_of_turn_silence_ms": 100,
            },
        },
    }


# ---------------------------------------------------------------------------
# 5. Server — HTTP + WebSocket proxy
# ---------------------------------------------------------------------------


async def websocket_handler(request):
    browser_ws = web.WebSocketResponse()
    await browser_ws.prepare(request)

    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with ClientSession() as http:
        async with http.ws_connect(AAI_URL, headers=headers) as aai_ws:
            await aai_ws.send_json(session_config())
            pending_tools: list[dict] = []

            async def browser_to_aai():
                async for msg in browser_ws:
                    if msg.type == WSMsgType.TEXT:
                        await aai_ws.send_str(msg.data)
                    elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        break

            async def aai_to_browser():
                async for msg in aai_ws:
                    if msg.type == WSMsgType.TEXT:
                        event = json.loads(msg.data)
                        t = event.get("type")

                        if t == "tool.call":
                            result = await execute_tool(event)
                            pending_tools.append(result)
                            await browser_ws.send_json(event)

                        elif t == "reply.done":
                            if event.get("status") == "interrupted":
                                pending_tools.clear()
                            elif pending_tools:
                                for tool in pending_tools:
                                    await aai_ws.send_json({
                                        "type": "tool.result",
                                        "call_id": tool["call_id"],
                                        "result": json.dumps(tool["result"]),
                                    })
                                pending_tools.clear()
                            await browser_ws.send_json(event)

                        else:
                            await browser_ws.send_json(event)
                    elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        break

            await asyncio.gather(browser_to_aai(), aai_to_browser())
    return browser_ws


async def index_handler(request):
    return web.FileResponse(Path(__file__).with_suffix(".html"))


app = web.Application()
app.router.add_get("/", index_handler)
app.router.add_get("/ws", websocket_handler)

if __name__ == "__main__":
    print(f"Bright Smile Dental Receptionist")
    print(f"Open http://localhost:{PORT}")
    web.run_app(app, port=PORT)
