# Plan: Cleaner Communication with Hexagonal Architecture

## Context

Smoobu's API only supports messaging guests and hosts — it cannot send messages to
cleaning personnel. We need a separate communication channel for cleaners, designed
so the channel is swappable (email now, WhatsApp/Telegram/multi-channel later).

This is a textbook case for hexagonal architecture (ports & adapters).

---

## 1. The Port: `CleanerNotifier`

The **port** is a Python abstract class that defines *what* the business logic needs
from cleaner communication, without caring *how* it happens.

```python
# src/communication/ports.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CleanerQuery:
    """What we send to the cleaner."""
    request_id: str
    cleaner_name: str
    guest_name: str
    property_name: str
    request_type: str          # "early_checkin" or "late_checkout"
    original_time: str         # "15:00"
    requested_time: str        # "12:00"
    date: str                  # "2026-02-20"
    message: str               # Human-readable question


@dataclass
class CleanerResponse:
    """What we get back from the cleaner."""
    request_id: str
    raw_text: str              # The cleaner's actual words
    received_at: datetime


class CleanerNotifier(ABC):
    """
    Port: how we communicate with cleaning staff.

    The business logic depends ONLY on this interface.
    It doesn't know or care whether messages go via email,
    WhatsApp, Telegram, or carrier pigeon.
    """

    @abstractmethod
    async def send_query(self, query: CleanerQuery) -> str:
        """
        Send a question to the cleaner.
        Returns a tracking ID (email Message-ID, chat message ID, etc.)
        """
        ...

    @abstractmethod
    async def poll_responses(self) -> list[CleanerResponse]:
        """
        Check for new responses from cleaners.
        Returns all unprocessed responses since last poll.
        """
        ...
```

**Why this shape?**

- `send_query` is fire-and-forget — the business logic sends the question, then
  moves on. It doesn't block waiting for a reply.
- `poll_responses` is called periodically by the scheduler. This works for both
  pull-based channels (email/IMAP) and push-based channels (webhook adapters that
  buffer incoming messages into a queue).
- The `request_id` in both dataclasses is the correlation key — it links a response
  back to the original query.

---

## 2. The First Adapter: Email

```python
# src/communication/email_notifier.py

import smtplib
import email.utils
from email.mime.text import MIMEText
from imapclient import IMAPClient
from .ports import CleanerNotifier, CleanerQuery, CleanerResponse


class EmailCleanerNotifier(CleanerNotifier):
    """Adapter: communicate with cleaners via email (SMTP send, IMAP receive)."""

    def __init__(self, config):
        self.smtp_host = config.email.smtp_host
        self.smtp_port = config.email.smtp_port
        self.smtp_user = config.email.smtp_user
        self.smtp_password = config.email.smtp_password
        self.imap_host = config.email.imap_host
        self.imap_port = config.email.imap_port
        self.cleaner_email = config.cleaning_staff[0].email  # TODO: multi-cleaner

    async def send_query(self, query: CleanerQuery) -> str:
        subject = f"[REQ-{query.request_id}] {query.property_name} - {query.date}"
        body = query.message

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = self.cleaner_email
        msg["Message-ID"] = email.utils.make_msgid(domain=self.smtp_host)

        # Embed request_id in a custom header for reliable correlation
        msg["X-Request-ID"] = query.request_id

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

        return msg["Message-ID"]

    async def poll_responses(self) -> list[CleanerResponse]:
        responses = []

        with IMAPClient(self.imap_host, port=self.imap_port, ssl=True) as client:
            client.login(self.smtp_user, self.smtp_password)
            client.select_folder("INBOX")

            # Search for unread replies from the cleaner
            uids = client.search(["UNSEEN", "FROM", self.cleaner_email])

            for uid in uids:
                raw = client.fetch([uid], ["RFC822"])
                msg = email.message_from_bytes(raw[uid][b"RFC822"])

                # Extract request_id from subject line: "[REQ-abc123] ..."
                subject = msg["Subject"] or ""
                request_id = self._extract_request_id(subject)

                if request_id:
                    body = self._get_body(msg)
                    responses.append(CleanerResponse(
                        request_id=request_id,
                        raw_text=body,
                        received_at=datetime.utcnow(),
                    ))
                    # Mark as seen
                    client.set_flags([uid], [b"\\Seen"])

        return responses

    def _extract_request_id(self, subject: str) -> str | None:
        # Matches "[REQ-abc123]" in subject or Re: [REQ-abc123] ...
        import re
        match = re.search(r"\[REQ-([^\]]+)\]", subject)
        return match.group(1) if match else None

    def _get_body(self, msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
        return msg.get_payload(decode=True).decode()
```

**Correlation strategy**: The `request_id` is embedded in the email subject as
`[REQ-{id}]`. When the cleaner hits "Reply", their email client preserves the
subject. We parse it back out on the receiving end.

---

## 3. Future Adapters (sketches)

### Telegram

```python
# src/communication/telegram_notifier.py

class TelegramCleanerNotifier(CleanerNotifier):
    """Adapter: communicate with cleaners via Telegram bot."""

    def __init__(self, config):
        self.bot_token = config.telegram.bot_token
        self.cleaner_chat_id = config.cleaning_staff[0].telegram_chat_id
        self._pending_responses: list[CleanerResponse] = []
        # Telegram webhook pushes to our endpoint, which calls _on_message()

    async def send_query(self, query: CleanerQuery) -> str:
        text = f"*{query.property_name} — {query.date}*\n\n{query.message}"
        result = await telegram_api.send_message(
            chat_id=self.cleaner_chat_id,
            text=text,
            parse_mode="Markdown",
        )
        # Store mapping: telegram_message_id -> request_id
        self._store_mapping(result.message_id, query.request_id)
        return str(result.message_id)

    async def poll_responses(self) -> list[CleanerResponse]:
        # Drain the buffer filled by the webhook handler
        responses = self._pending_responses.copy()
        self._pending_responses.clear()
        return responses

    async def handle_webhook(self, update: dict):
        """Called by our FastAPI endpoint when Telegram sends an update."""
        reply_to = update["message"].get("reply_to_message", {}).get("message_id")
        request_id = self._lookup_request_id(reply_to)
        if request_id:
            self._pending_responses.append(CleanerResponse(
                request_id=request_id,
                raw_text=update["message"]["text"],
                received_at=datetime.utcnow(),
            ))
```

### WhatsApp Cloud API

```python
# src/communication/whatsapp_notifier.py

class WhatsAppCleanerNotifier(CleanerNotifier):
    """Adapter: communicate via WhatsApp Cloud API."""

    def __init__(self, config):
        self.phone_number_id = config.whatsapp.phone_number_id
        self.access_token = config.whatsapp.access_token
        self.cleaner_phone = config.cleaning_staff[0].phone
        self._pending_responses: list[CleanerResponse] = []

    async def send_query(self, query: CleanerQuery) -> str:
        # WhatsApp Cloud API — send a text message
        result = await self._api_call("POST", f"/{self.phone_number_id}/messages", {
            "messaging_product": "whatsapp",
            "to": self.cleaner_phone,
            "type": "text",
            "text": {"body": f"[REQ-{query.request_id}]\n\n{query.message}"},
        })
        return result["messages"][0]["id"]

    async def poll_responses(self) -> list[CleanerResponse]:
        responses = self._pending_responses.copy()
        self._pending_responses.clear()
        return responses

    async def handle_webhook(self, payload: dict):
        """Called by our FastAPI endpoint when WhatsApp sends a webhook."""
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                for msg in change.get("value", {}).get("messages", []):
                    # Extract request_id from message context or text
                    request_id = self._extract_request_id(msg["text"]["body"])
                    if request_id:
                        self._pending_responses.append(CleanerResponse(
                            request_id=request_id,
                            raw_text=msg["text"]["body"],
                            received_at=datetime.utcnow(),
                        ))
```

### Console (for development/testing)

```python
# src/communication/console_notifier.py

class ConsoleCleanerNotifier(CleanerNotifier):
    """Adapter: print to console, read from stdin. For development only."""

    def __init__(self):
        self._pending: list[CleanerResponse] = []

    async def send_query(self, query: CleanerQuery) -> str:
        print(f"\n{'='*60}")
        print(f"TO CLEANER: {query.cleaner_name}")
        print(f"RE: {query.property_name} — {query.date}")
        print(f"{'='*60}")
        print(query.message)
        print(f"{'='*60}\n")
        return f"console-{query.request_id}"

    async def poll_responses(self) -> list[CleanerResponse]:
        responses = self._pending.copy()
        self._pending.clear()
        return responses

    def simulate_response(self, request_id: str, text: str):
        """Call this from tests or a dev CLI to simulate a cleaner reply."""
        self._pending.append(CleanerResponse(
            request_id=request_id,
            raw_text=text,
            received_at=datetime.utcnow(),
        ))
```

---

## 4. Wiring: How the Adapter Gets Chosen

A simple factory based on config — no DI framework needed.

```python
# src/communication/factory.py

from .ports import CleanerNotifier
from .email_notifier import EmailCleanerNotifier
from .console_notifier import ConsoleCleanerNotifier


def create_cleaner_notifier(config) -> CleanerNotifier:
    """Factory: pick the right adapter based on config."""

    channel = config.cleaning_staff_channel  # "email", "telegram", "whatsapp", "console"

    if channel == "email":
        return EmailCleanerNotifier(config)
    elif channel == "telegram":
        from .telegram_notifier import TelegramCleanerNotifier
        return TelegramCleanerNotifier(config)
    elif channel == "whatsapp":
        from .whatsapp_notifier import WhatsAppCleanerNotifier
        return WhatsAppCleanerNotifier(config)
    elif channel == "console":
        return ConsoleCleanerNotifier()
    else:
        raise ValueError(f"Unknown cleaner channel: {channel}")
```

```yaml
# config.yaml — just change this one line to switch channels
cleaning_staff_channel: "email"   # or "telegram", "whatsapp", "console"
```

---

## 5. How the Business Logic Uses the Port

The processor never imports any adapter — only the port.

```python
# src/business_logic/processor.py

from communication.ports import CleanerNotifier, CleanerQuery


class RequestProcessor:
    def __init__(self, cleaner_notifier: CleanerNotifier, ...):
        self.cleaner = cleaner_notifier   # injected, could be any adapter

    async def handle_checkin_request(self, request):
        query = CleanerQuery(
            request_id=request.id,
            cleaner_name="Marie",
            guest_name=request.guest_name,
            property_name=request.property_name,
            request_type=request.request_type,
            original_time=request.original_checkin.strftime("%H:%M"),
            requested_time=request.requested_checkin.strftime("%H:%M"),
            date=request.requested_checkin.strftime("%Y-%m-%d"),
            message=self.ai.generate_cleaner_question(request),
        )
        tracking_id = await self.cleaner.send_query(query)
        request.cleaner_tracking_id = tracking_id
        request.status = "pending_cleaner"
```

And the scheduler calls `poll_responses()` periodically:

```python
# src/scheduler.py

async def check_cleaner_responses(cleaner_notifier, processor):
    """Called every 60 seconds by APScheduler."""
    responses = await cleaner_notifier.poll_responses()
    for response in responses:
        await processor.handle_cleaner_response(response)
```

---

## 6. Dependency Graph (What Depends on What)

```
business_logic/processor.py  ──depends on──▶  communication/ports.py (abstract)
                                                       ▲
                                                       │ implements
                                    ┌──────────────────┼──────────────────┐
                                    │                  │                  │
                          email_notifier.py   telegram_notifier.py   console_notifier.py
                                    │
                              uses smtplib,
                              imapclient
```

The arrows point inward — adapters depend on the port, not the other way around.
The business logic never touches smtplib, Telegram SDK, or any channel-specific code.

---

## 7. Files to Create / Modify

### New files

| File | Purpose |
|---|---|
| `src/communication/ports.py` | Port: `CleanerNotifier` ABC + dataclasses |
| `src/communication/email_notifier.py` | Adapter: Email (SMTP/IMAP) |
| `src/communication/console_notifier.py` | Adapter: Console (for dev/testing) |
| `src/communication/factory.py` | Factory: create adapter from config |
| `tests/test_cleaner_notifier.py` | Tests against the port interface |

### Files to modify

| File | Change |
|---|---|
| `ARCHITECTURE.md` | Update Phase 0 — Smoobu can't reach cleaners, we use a separate channel via the port |
| `ARCHITECTURE.md` | Update cleaning staff config to include `cleaning_staff_channel` |
| `ARCHITECTURE.md` | Replace the "Cleaning Staff Comms (Email Adapter)" box in the diagram with the ports/adapters pattern |
| `.env.example` | Add `CLEANING_STAFF_CHANNEL=email` |
| `config.yaml` (when created) | Add `cleaning_staff_channel` setting |

---

## 8. Implementation Order

1. **`ports.py`** — Define the interface. This is the contract everything else depends on.
2. **`console_notifier.py`** — Simplest adapter. Lets us test the full flow without any external service.
3. **`factory.py`** — Wiring.
4. **`email_notifier.py`** — Real adapter for production.
5. **`tests/test_cleaner_notifier.py`** — Test both adapters against the same interface.
6. **Update `ARCHITECTURE.md`** — Document the design decision and update Phase 0.

---

## 9. What Changes in Phase 0

Phase 0 originally assumed Smoobu could be the "single messaging hub" for both
guests and cleaners. We now know Smoobu only supports guest ↔ host messaging.

**Updated Phase 0 scope**:
- Guest messaging: Smoobu API (unchanged)
- Cleaner messaging: `CleanerNotifier` port with `ConsoleCleanerNotifier` adapter
- Prove the round-trip: guest message in → cleaner query out → cleaner response in → guest reply out
- Email adapter comes in Phase 1 (or late Phase 0 if we want to test it early)

This is actually *better* than the original plan — the console adapter lets us
test the full flow without needing a Gmail account set up.

---

## 10. The Second Port: `SmoobuGateway`

Smoobu is the other external integration. Same hexagonal pattern: a port defines
what the business logic needs, adapters provide real and simulated implementations.

```python
# src/adapters/ports.py

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GuestMessage:
    """A message from a guest, read from Smoobu."""
    message_id: int
    subject: str
    body: str


class SmoobuGateway(ABC):
    """
    Port: how we interact with Smoobu for guest messaging.

    The business logic depends ONLY on this interface.
    """

    @abstractmethod
    def get_messages(self, reservation_id: int) -> list[GuestMessage]:
        """Read all messages for a reservation."""
        ...

    @abstractmethod
    def send_message(self, reservation_id: int, subject: str, body: str) -> None:
        """Send a message to the guest on a reservation."""
        ...
```

### Real adapter: `SmoobuClient`

Uses the `requests` library to call the Smoobu REST API.

```python
# src/adapters/smoobu_client.py

class SmoobuClient(SmoobuGateway):
    BASE_URL = "https://login.smoobu.com/api"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_messages(self, reservation_id):
        # GET /reservations/{id}/messages
        ...

    def send_message(self, reservation_id, subject, body):
        # POST /reservations/{id}/messages/send-message-to-guest
        ...
```

### Simulator adapter: `SimulatorSmoobuGateway`

In-memory fake. No mocking framework — just a plain Python class that records
sent messages and lets tests inject guest messages.

```python
# src/adapters/simulator_smoobu.py

class SimulatorSmoobuGateway(SmoobuGateway):
    def __init__(self):
        self._messages: dict[int, list[GuestMessage]] = {}
        self._sent: list[tuple[int, str, str]] = []

    def inject_guest_message(self, reservation_id, subject, body):
        """Test helper: simulate a guest sending a message."""
        ...

    def get_messages(self, reservation_id):
        return self._messages.get(reservation_id, [])

    def send_message(self, reservation_id, subject, body):
        self._sent.append((reservation_id, subject, body))
        # Also add to messages so get_messages sees it
        ...
```

---

## 11. Testing Strategy

Two external integrations tested independently with integration tests, plus
simulators for testing the full roundtrip in-memory. No mocking framework.

### Layer 1: Email integration test (exists)

`tests/test_email_roundtrip.py` — already implemented.

- Tests `EmailCleanerNotifier` with real Gmail accounts
- Send query → cleaner replies → poll and find the reply
- Skipped if credentials are not set

### Layer 2: Smoobu integration test (new)

`tests/test_smoobu_roundtrip.py` — tests `SmoobuClient` against the real API.

- Read messages for a test booking
- Send a message to the test booking
- Read messages again, verify the new message appears
- Skipped if `SMOOBU_API_KEY` is not set

```
send_message(booking, "test subject", "test body")
messages_after = get_messages(booking)
assert any message contains "test body"
```

### Layer 3: Roundtrip test with simulators (new)

`tests/test_roundtrip.py` — tests the full message flow in-memory.

Uses `SimulatorSmoobuGateway` + `ConsoleCleanerNotifier` (which already has
`simulate_response`). No network, no credentials, runs anywhere.

```
1. Inject a guest message into SimulatorSmoobuGateway
2. Orchestrator reads it, forwards to ConsoleCleanerNotifier
3. Simulate a cleaner response via ConsoleCleanerNotifier.simulate_response()
4. Orchestrator polls the response, sends reply via SimulatorSmoobuGateway
5. Assert: SimulatorSmoobuGateway recorded the outgoing reply
```

This proves the orchestration logic wires correctly without any external
dependency.

### Summary

| Test file | What it proves | External deps? |
|---|---|---|
| `test_email_roundtrip.py` | Email send/receive works | Gmail SMTP/IMAP |
| `test_smoobu_roundtrip.py` | Smoobu read/send works | Smoobu API |
| `test_roundtrip.py` | Full orchestration wires correctly | None |

---

## 12. Updated File List

### New files (this iteration)

| File | Purpose |
|---|---|
| `src/adapters/ports.py` | Port: `SmoobuGateway` ABC + `GuestMessage` dataclass |
| `src/adapters/smoobu_client.py` | Adapter: real Smoobu HTTP client |
| `src/adapters/simulator_smoobu.py` | Simulator: in-memory fake for testing |
| `tests/test_smoobu_roundtrip.py` | Integration test: real Smoobu API |
| `tests/test_roundtrip.py` | Roundtrip test: simulators only |

### Files to modify

| File | Change |
|---|---|
| `requirements.txt` | Add `requests` |
| `.env.example` | Already has `SMOOBU_API_KEY` and `TEST_BOOKING_ID` |
