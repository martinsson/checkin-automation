# Airbnb Check-In/Check-Out Automation System
## System Architecture & Functional Specification

---

## Executive Summary

This document describes an automated system for handling early check-in and late check-out requests for Airbnb properties. The system coordinates between guests (via Smoobu), cleaning personnel (via email), and the property manager (via Trello tasks), using AI to handle routine communications while escalating exceptions to human oversight.

---

## 1. System Overview

### 1.1 Purpose

Automate the repetitive process of coordinating early check-in and late check-out requests by:

- Detecting and parsing guest requests from Smoobu messages
- Communicating with cleaning staff to verify availability
- Generating appropriate responses to guests
- Creating tasks for human oversight when needed
- Generating new door codes when check-in/out times change

### 1.2 Design Principles

- **Modular architecture**: Messaging channels are pluggable and interchangeable
- **Human-in-the-loop**: Critical decisions and exceptions require approval
- **Fail-safe**: System escalates to human operator when uncertain or time-sensitive
- **Time-aware**: Business logic considers proximity to check-in date and response delays

---

## 2. Architecture Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Message Ingestion Layer                       │
│                          (Smoobu Adapter)                            │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AI Processing Engine                             │
│                    (Business Logic Core)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Intent      │  │  Information │  │   Response   │              │
│  │  Detection   │→ │  Extraction  │→ │  Generation  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└───┬─────────────────────────────────────────────────────────────┬───┘
    │                                                             │
    ▼                                                             ▼
┌─────────────────────────┐                          ┌──────────────────┐
│  Cleaning Staff Comms   │                          │  Guest Response  │
│    (Email Adapter)      │                          │  (Smoobu API)    │
└─────────────────────────┘                          └──────────────────┘
    │                                                             │
    ▼                                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Task Management Module                           │
│                        (Trello API)                                  │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Door Code Management                              │
│                   (Smart Lock API)                                   │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Data Storage & State Management                         │
│                      (SQLite)                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 Message Ingestion Layer

**Purpose**: Receive and queue guest messages from various sources via webhooks.

**Initial Implementation**: Smoobu webhook endpoint (event-driven, real-time)

**Smoobu Webhook Events**:
- `newMessage` - New guest message received ⭐ (primary event)
- `newReservation` - New booking created
- `updateReservation` - Booking updated
- `cancelReservation` - Booking cancelled

**API Documentation**: https://docs.smoobu.com

**Webhook Setup**:
1. Configure webhook URL in Smoobu: `Advanced > API Keys > Webhook URLs`
2. Smoobu sends POST requests to your endpoint when events occur
3. Your endpoint acknowledges receipt (return 200 OK)
4. Fetch full message details via API

**Incoming Webhook Payload** (`newMessage`):
```json
{
  "action": "newMessage",
  "user": 7,
  "data": {
    "id": 1234,
    "sender": "guest",
    "booking": {
      "id": 234
    }
  }
}
```

**Fetch Full Message Details**:
```bash
GET https://login.smoobu.com/api/reservations/{bookingId}/messages
Headers: Api-Key: {your_api_key}
```

**Output**: Standardized message object
```python
{
    "id": "msg_12345",
    "source": "smoobu",
    "property_id": "prop_abc",
    "guest_name": "John Doe",
    "guest_email": "john@example.com",
    "booking_id": "book_xyz",
    "check_in": "2026-02-20",
    "check_out": "2026-02-25",
    "message_text": "Hi, is it possible to check in at 12pm instead of 3pm?",
    "timestamp": "2026-02-11T14:30:00Z",
    "webhook_received_at": "2026-02-11T14:30:05Z"
}
```

**Future Flexibility**: Adapter pattern allows adding:
- Email forwarding (for properties not on Smoobu)
- Direct Airbnb API webhooks
- Other property management platforms

### 2.2 AI Processing Engine (Business Logic Core)

**Purpose**: Analyze messages, extract intent, make decisions, and generate responses.

**Technology**: Claude API (Anthropic) or similar LLM with structured prompts

**Key Functions**:

1. **Request Detection**: Identify early check-in or late check-out requests
2. **Information Extraction**: Parse requested time, booking dates, property ID, guest details
3. **Query Generation**: Create appropriate message to cleaning staff
4. **Response Parsing**: Understand cleaning staff confirmations/rejections
5. **Reply Composition**: Draft appropriate guest response (approval/denial)
6. **Escalation Logic**: Determine when human intervention is needed

**Example Prompt Structure**:
```python
SYSTEM_PROMPT = """
You are an Airbnb property management assistant. Analyze guest messages to:
1. Detect check-in/out time change requests
2. Extract: property, current times, requested times, urgency
3. Generate queries for cleaning staff
4. Parse cleaner responses
5. Draft guest replies

Output structured JSON with extracted information and recommended actions.
"""
```

### 2.3 Cleaning Staff Communication Module

**Purpose**: Send queries and receive responses from cleaning personnel.

**Initial Implementation**: Email (SMTP/IMAP)

**Future Options**: WhatsApp Business API, SMS, Slack, or dedicated app

**Key Features**:
- Template-based message formatting
- Response monitoring with timeout detection
- Thread tracking to match responses to requests
- Multi-recipient support (cleaning team distribution list)

**Email Template Example**:
```
Subject: Check-in Request - Property A - Feb 20

Hi Team,

Guest John Doe has requested an early check-in:
- Property: Apartment A
- Original check-in: 3:00 PM, Feb 20
- Requested check-in: 12:00 PM, Feb 20

Can the cleaning be completed by 11:30 AM?

Please reply with YES or NO.

Thanks!
```

### 2.4 Guest Response Module

**Purpose**: Send final responses back to guests via Smoobu.

**Implementation**: Smoobu API or email integration

**Key Features**:
- Personalized message generation
- Door code inclusion when applicable
- Multi-language support (if needed)
- Tone matching (friendly, professional)

**Response Template Examples**:
```
APPROVED:
"Great news! We can accommodate your early check-in at 12:00 PM on Feb 20. 
Your updated door code is: 1234#
Looking forward to welcoming you!"

DENIED:
"Thank you for your request. Unfortunately, we cannot accommodate an early 
check-in at 12:00 PM as cleaning will not be complete. Your original 
check-in time of 3:00 PM remains confirmed. See you then!"
```

### 2.5 Task Management Module

**Purpose**: Create actionable tasks for human oversight and approval.

**Implementation**: Trello API integration

**Task Types**:
1. **Approval Required**: Review and approve drafted response before sending
2. **Exception Handling**: Handle edge cases (no cleaner response, conflict, ambiguity)
3. **Door Code Update**: Confirm new code has been generated and communicated
4. **Urgent**: Same-day or immediate attention required

**Trello Card Structure**:
```
Title: [URGENT] Check-in Request - John Doe - Property A

Description:
---
REQUEST DETAILS:
- Guest: John Doe
- Property: Apartment A
- Original: 3:00 PM, Feb 20
- Requested: 12:00 PM, Feb 20
- Status: Awaiting cleaner response

CLEANER RESPONSE:
[Pending - no response after 2 hours]

DRAFTED REPLY:
[System unable to generate - escalating to you]

ACTIONS NEEDED:
[ ] Contact cleaning staff directly
[ ] Approve/deny request
[ ] Generate new door code if approved
[ ] Send response to guest

---
Labels: urgent, check-in, needs-approval
Due Date: Feb 20, 11:00 AM
```

### 2.6 Door Code Management Module

**Purpose**: Generate time-based access codes for modified check-in/out times.

**Implementation**: Integration with smart lock system API (e.g., August, Yale, Nuki, RemoteLock)

**Functionality**:
- Generate unique codes with custom validity periods
- Update existing reservation codes if times change
- Log all code changes for audit trail
- Automatic code expiration

**API Example (RemoteLock)**:
```python
def generate_door_code(property_id, start_time, end_time):
    response = remotelock_api.create_access_code(
        device_id=property_id,
        code=generate_random_code(),
        starts_at=start_time,
        ends_at=end_time,
        name=f"Guest_{booking_id}"
    )
    return response.code
```

### 2.7 Data Storage & State Management

**Purpose**: Track request lifecycle and maintain conversation context.

**Implementation**: SQLite database (lightweight, file-based, perfect for small VPS)

**Schema**:

```sql
-- Main requests table
CREATE TABLE requests (
    id TEXT PRIMARY KEY,
    source TEXT,  -- 'smoobu', 'email', etc.
    property_id TEXT,
    guest_name TEXT,
    guest_email TEXT,
    booking_id TEXT,
    original_checkin DATETIME,
    original_checkout DATETIME,
    requested_checkin DATETIME,
    requested_checkout DATETIME,
    request_type TEXT,  -- 'early_checkin', 'late_checkout'
    status TEXT,  -- 'new', 'pending_cleaner', 'pending_approval', 'approved', 'denied', 'sent'
    urgency TEXT,  -- 'normal', 'urgent', 'critical'
    created_at DATETIME,
    updated_at DATETIME
);

-- Message history
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT,
    direction TEXT,  -- 'inbound_guest', 'outbound_cleaner', 'inbound_cleaner', 'outbound_guest'
    content TEXT,
    timestamp DATETIME,
    FOREIGN KEY (request_id) REFERENCES requests(id)
);

-- Cleaner responses
CREATE TABLE cleaner_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT,
    cleaner_email TEXT,
    response TEXT,  -- 'yes', 'no', 'maybe', 'unclear'
    raw_message TEXT,
    received_at DATETIME,
    FOREIGN KEY (request_id) REFERENCES requests(id)
);

-- Door codes
CREATE TABLE door_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT,
    property_id TEXT,
    code TEXT,
    valid_from DATETIME,
    valid_until DATETIME,
    created_at DATETIME,
    FOREIGN KEY (request_id) REFERENCES requests(id)
);

-- Configuration
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

---

## 3. Business Logic & Decision Rules

### 3.1 Request Processing Flow

```
1. Message Arrival → System detects new message from guest
2. Intent Classification → AI determines if it's a check-in/out request
3. Information Extraction → Parse property, dates, requested time
4. Feasibility Check → Query cleaning staff via email
5. Await Response → Monitor for cleaner reply (with timeout)
6. Response Processing → Parse cleaner's confirmation/rejection
7. Draft Reply → AI generates appropriate guest response
8. Human Approval → Create Trello task for manager review
9. Send Response → Upon approval, send to guest via Smoobu
10. Update Door Code → Generate new code if check-in/out time changed
```

### 3.2 Escalation Triggers (Human Intervention Required)

The system creates a Trello task and pauses automated processing when:

- **No Cleaner Response**: No reply received within 2 hours (configurable)
- **Urgent Request**: Request is for same-day or next-day (less than 24 hours away)
- **Ambiguous Request**: AI cannot confidently extract required information (confidence < 80%)
- **Conflicting Information**: Cleaner says 'maybe' or provides conditional response
- **Special Requests**: Guest includes additional unusual requests beyond time change
- **System Error**: Any component failure (email not sending, API timeout, etc.)
- **Close to Date**: Request received within 48 hours of check-in time

### 3.3 Time-Based Rules

**Immediate Escalation** (< 12 hours to check-in):
- Create URGENT Trello task
- Send SMS/push notification to manager
- Do not wait for cleaner response
- Requires immediate human decision

**Fast Track** (12-24 hours to check-in):
- Reduce cleaner response timeout to 1 hour
- Create high-priority Trello task
- Send notification if no cleaner response

**Standard Processing** (24+ hours to check-in):
- Normal 2-hour cleaner response timeout
- Standard approval workflow
- Regular Trello task priority

### 3.4 Automatic Approval Conditions

The system can send automatic approvals (without creating Trello task) if ALL conditions are met:

- Request is > 48 hours before check-in
- Cleaner responds affirmatively within timeout
- No special requests or complications
- Property has automatic approval enabled in config
- Request is standard (early check-in between 12-3pm, late checkout between 11am-1pm)

**Note**: This feature should be opt-in and configurable per property.

---

## 4. Use Case Scenarios

### 4.1 Scenario: Happy Path (All Automatic)

**Context**: Guest requests early check-in 5 days in advance, cleaner confirms quickly, automatic approval enabled

**Flow**:
1. ✅ **T+0min**: Guest message arrives: "Can we check in at 1pm instead of 3pm?"
2. ✅ **T+1min**: AI detects request, extracts info, confidence: 95%
3. ✅ **T+2min**: Email sent to cleaner: "Can cleaning be done by 12:30pm on Feb 20?"
4. ✅ **T+45min**: Cleaner replies: "Yes, no problem"
5. ✅ **T+46min**: AI parses response, confidence: 98%
6. ✅ **T+47min**: System generates new door code: 5678#
7. ✅ **T+48min**: Draft response created
8. ✅ **T+49min**: Auto-approval criteria met, message sent to guest
9. ✅ **T+50min**: Confirmation logged, request marked as 'completed'

**Result**: Fully automated, no human intervention required, completed in ~50 minutes.

### 4.2 Scenario: Cleaner Does Not Respond

**Context**: Guest requests early check-in, but cleaner doesn't respond within timeout

**Flow**:
1. ✅ **T+0min**: Guest message: "Can we arrive at noon instead of 3pm?"
2. ✅ **T+1min**: AI processes, sends email to cleaner
3. ⏳ **T+30min**: No response yet, system continues monitoring
4. ⏳ **T+1hr**: Still no response, system continues monitoring
5. ⏳ **T+2hr**: Timeout reached, no cleaner response
6. ⚠️ **T+2hr 1min**: System creates Trello card:
   ```
   Title: [NEEDS ATTENTION] No Cleaner Response - John Doe - Property A
   
   Labels: needs-response, check-in
   Priority: Medium
   
   Description:
   Guest requested early check-in (12pm vs 3pm) for Feb 20.
   Cleaning staff has not responded after 2 hours.
   
   ACTIONS:
   [ ] Contact cleaning staff directly
   [ ] Make decision on request
   [ ] Send response to guest
   ```
7. 📧 **T+2hr 2min**: Notification email sent to manager
8. 👤 **T+3hr**: Manager contacts cleaner directly via phone
9. 👤 **T+3hr 15min**: Manager updates Trello card, approves request
10. ✅ **T+3hr 20min**: System detects approval, generates code, sends guest response

**Result**: System escalated appropriately when timeout occurred, manager resolved manually.

### 4.3 Scenario: Urgent Same-Day Request

**Context**: Guest requests early check-in on the same day (6 hours before check-in)

**Flow**:
1. ⚠️ **T+0min**: Guest message: "We're arriving early, can we check in at 11am? We're 2 hours away"
2. ⚠️ **T+1min**: AI detects URGENT (< 12 hours to check-in)
3. ⚠️ **T+2min**: System immediately creates URGENT Trello card
4. 📧 **T+2min**: SMS sent to manager: "URGENT: Same-day check-in request"
5. 📧 **T+3min**: Email still sent to cleaner (parallel track)
6. 👤 **T+10min**: Manager sees notification, calls cleaner directly
7. 👤 **T+15min**: Manager confirms with cleaner, approves in Trello
8. ✅ **T+16min**: System generates door code
9. ✅ **T+17min**: Response sent to guest: "Yes, early check-in approved! Code: 9876#"

**Result**: Urgent request handled with human oversight, resolved within 17 minutes.

### 4.4 Scenario: Ambiguous Request

**Context**: Guest message is unclear or contains multiple requests

**Flow**:
1. ❓ **T+0min**: Guest message: "Hi! We might arrive early, maybe around lunchtime? Also, is there parking? And can we bring our dog?"
2. ❓ **T+1min**: AI processes message
   - Detects possible check-in request (confidence: 65%)
   - Unclear timing ("maybe", "lunchtime" = ambiguous)
   - Additional questions present
3. ⚠️ **T+2min**: Confidence < 80% → Escalation triggered
4. ⚠️ **T+3min**: Trello card created:
   ```
   Title: [NEEDS CLARIFICATION] Ambiguous Request - Jane Smith
   
   Labels: needs-clarification, multiple-questions
   
   Description:
   Guest sent unclear message with multiple questions.
   
   ORIGINAL MESSAGE:
   "Hi! We might arrive early, maybe around lunchtime? 
   Also, is there parking? And can we bring our dog?"
   
   AI ANALYSIS:
   - Possible early check-in request (not confirmed)
   - Time unclear ("lunchtime" could be 11am-2pm)
   - Additional questions: parking, pet policy
   - Confidence: 65% (below threshold)
   
   RECOMMENDED ACTION:
   Send clarifying message to guest asking for:
   1. Specific desired check-in time
   2. Confirmation of parking/pet questions separately
   ```
5. 👤 **T+30min**: Manager reviews, sends clarifying message
6. ✅ **T+2hr**: Guest clarifies: "Check-in at 1pm please"
7. ✅ Process continues normally from here

**Result**: System correctly identified ambiguity and escalated for human clarification.

### 4.5 Scenario: Conditional Cleaner Response

**Context**: Cleaner gives a "maybe" or conditional answer

**Flow**:
1. ✅ **T+0min**: Guest requests early check-in at 12pm
2. ✅ **T+1min**: Email sent to cleaner
3. ⚠️ **T+30min**: Cleaner replies: "Maybe, depends if the current guest checks out on time"
4. ⚠️ **T+31min**: AI parses response:
   - Sentiment: uncertain
   - Keywords detected: "maybe", "depends"
   - Confidence in approval: 40%
5. ⚠️ **T+32min**: Conditional response → Escalation
6. ⚠️ **T+33min**: Trello card created:
   ```
   Title: [CONDITIONAL] Check-in Request - Needs Decision
   
   Description:
   Cleaner response is conditional/uncertain.
   
   CLEANER SAID:
   "Maybe, depends if the current guest checks out on time"
   
   OPTIONS:
   A) Approve conditionally: "We'll do our best for 12pm, but 3pm guaranteed"
   B) Deny and keep original time: "3pm check-in remains"
   C) Wait and confirm later: "Let me check with cleaning at 10am tomorrow"
   ```
7. 👤 **T+1hr**: Manager selects option A, edits draft message
8. ✅ **T+1hr 5min**: Approved message sent to guest

**Result**: System recognized conditional answer and provided manager with clear options.

### 4.6 Scenario: Multiple Simultaneous Requests

**Context**: Two guests request changes for the same property on overlapping dates

**Flow**:
1. ✅ **T+0min**: Guest A requests late checkout (1pm) for Feb 20
2. ✅ **T+5min**: Guest B requests early check-in (12pm) for Feb 20
3. ⚠️ **T+6min**: System detects conflict:
   - Same property
   - Late checkout at 1pm conflicts with early check-in at 12pm
   - Impossible to satisfy both
4. ⚠️ **T+7min**: Trello card created:
   ```
   Title: [CONFLICT] Overlapping Requests - Property A - Feb 20
   
   Labels: conflict, urgent
   
   Description:
   Two guests have conflicting requests for same property/date:
   
   REQUEST 1 (arrived first):
   - Guest A: Late checkout at 1:00 PM
   
   REQUEST 2 (arrived 5min later):
   - Guest B: Early check-in at 12:00 PM
   
   CONFLICT:
   Checkout at 1pm leaves no time for cleaning before 12pm check-in.
   
   OPTIONS:
   1. Approve late checkout, deny early check-in
   2. Deny late checkout, approve early check-in
   3. Compromise: checkout 11am, check-in 1pm
   4. Contact both guests with alternative options
   ```
5. 👤 **T+30min**: Manager decides on option 1
6. ✅ **T+35min**: Responses sent to both guests

**Result**: System detected scheduling conflict and provided clear decision options.

---

## 5. Technical Implementation Details

### 5.1 Recommended Tech Stack

**Runtime**:
- **Language**: Python 3.11+
- **Framework**: FastAPI (for webhooks/API) or simple polling script
- **Task Queue**: APScheduler (for periodic checks) or Celery (if scaling needed)

**Libraries**:
```python
# Core
fastapi==0.104.0
pydantic==2.4.0
sqlalchemy==2.0.0
alembic==1.12.0  # database migrations

# AI
anthropic==0.7.0  # Claude API
openai==1.3.0     # Alternative: OpenAI

# Communication
smtplib  # Built-in (email sending)
imapclient==2.3.1  # Email receiving
requests==2.31.0  # API calls

# Integrations
py-trello==0.19.0  # Trello API
python-dateutil==2.8.2

# Utilities
python-dotenv==1.0.0
loguru==0.7.2  # Better logging
```

**Database**: SQLite (included with Python)

**Hosting**: Small VPS (2GB RAM, 1 CPU sufficient)
- DigitalOcean Droplet ($12/month)
- Hetzner Cloud CX11 (€4/month)
- Raspberry Pi 4 (self-hosted)

### 5.2 Project Structure

```
airbnb-automation/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── config.yaml
├── docker-compose.yml      # Optional: for containerized deployment
│
├── docs/                   # Documentation & specs
│   ├── ARCHITECTURE.md     # This document
│   ├── API_INTEGRATION.md  # Smoobu API integration guide
│   ├── DEPLOYMENT.md       # Deployment instructions
│   ├── api-specs/          # External API specifications
│   │   ├── smoobu/         # Smoobu API docs
│   │   │   ├── README.md   # Link: https://docs.smoobu.com
│   │   │   └── webhooks.md # Webhook event documentation
│   │   ├── trello/         # Trello API docs
│   │   └── remotelock/     # Smart lock API docs
│   └── diagrams/           # Architecture diagrams (optional)
│
├── main.py                 # Entry point (webhook server)
├── scheduler.py            # Background task scheduler (timeouts, cleanup)
│
├── api/                    # API/Webhook endpoints
│   ├── __init__.py
│   ├── webhooks.py         # Webhook handlers (Smoobu, etc.)
│   ├── health.py           # Health check endpoint
│   └── middleware.py       # Request validation, auth
│
├── adapters/               # Messaging adapters (pluggable)
│   ├── __init__.py
│   ├── base.py            # Abstract base class
│   ├── smoobu.py          # Smoobu webhook + API integration
│   ├── email.py           # Email ingestion (fallback)
│   └── airbnb.py          # Future: Direct Airbnb API
│
├── ai/                     # AI processing
│   ├── __init__.py
│   ├── client.py          # Claude API client
│   ├── prompts.py         # Prompt templates
│   └── parsers.py         # Response parsing logic
│
├── communication/          # Outbound messaging
│   ├── __init__.py
│   ├── cleaner_email.py   # Email to cleaning staff
│   ├── guest_response.py  # Responses via Smoobu
│   └── notifications.py   # SMS/push to manager
│
├── integrations/           # External services
│   ├── __init__.py
│   ├── trello_client.py   # Trello API
│   ├── door_lock.py       # Smart lock integration
│   └── calendar.py        # iCal/booking calendar
│
├── models/                 # Data models
│   ├── __init__.py
│   ├── database.py        # SQLAlchemy setup
│   ├── request.py         # Request model
│   ├── message.py         # Message model
│   └── config.py          # Configuration model
│
├── business_logic/         # Core logic
│   ├── __init__.py
│   ├── processor.py       # Main request processor
│   ├── escalation.py      # Escalation rules
│   ├── approval.py        # Auto-approval logic
│   └── state_machine.py   # Workflow state management
│
├── utils/                  # Utilities
│   ├── __init__.py
│   ├── logger.py          # Logging setup
│   ├── time_utils.py      # Timezone handling
│   └── validators.py      # Input validation
│
├── tests/                  # Unit tests
│   ├── __init__.py
│   ├── test_ai.py
│   ├── test_processor.py
│   ├── test_webhooks.py   # Webhook endpoint tests
│   └── test_scenarios.py
│
├── migrations/             # Database migrations
│   └── versions/
│
└── data/                   # Runtime data (gitignored)
    ├── database.db         # SQLite database
    └── logs/               # Application logs
```

### 5.3 Configuration File Example

```yaml
# config.yaml

general:
  timezone: "Europe/Paris"
  default_language: "en"

properties:
  - id: "prop_a"
    name: "Apartment A"
    address: "123 Rue Example"
    default_checkin: "15:00"
    default_checkout: "11:00"
    auto_approval_enabled: true
    lock_id: "lock_abc123"
    
  - id: "prop_b"
    name: "Villa B"
    address: "456 Avenue Sample"
    default_checkin: "16:00"
    default_checkout: "10:00"
    auto_approval_enabled: false
    lock_id: "lock_xyz789"

cleaning_staff:
  - email: "cleaner1@example.com"
    name: "Marie"
    properties: ["prop_a", "prop_b"]
  - email: "cleaner2@example.com"
    name: "Sophie"
    properties: ["prop_a"]

timeouts:
  cleaner_response: 7200  # 2 hours in seconds
  cleaner_response_urgent: 3600  # 1 hour for urgent
  
escalation:
  urgent_threshold_hours: 12  # Less than 12h = urgent
  critical_threshold_hours: 6  # Less than 6h = critical
  min_confidence: 0.80  # AI confidence threshold

auto_approval:
  enabled: true
  min_advance_hours: 48  # Only auto-approve if > 48h advance
  allowed_checkin_range:  # Can only auto-approve within these times
    earliest: "12:00"
    latest: "15:00"
  allowed_checkout_range:
    earliest: "11:00"
    latest: "13:00"

notifications:
  manager_email: "manager@example.com"
  manager_sms: "+33612345678"  # For urgent notifications
  
integrations:
  smoobu:
    api_key: "${SMOOBU_API_KEY}"
    webhook_secret: "${SMOOBU_WEBHOOK_SECRET}"
    
  trello:
    api_key: "${TRELLO_API_KEY}"
    api_token: "${TRELLO_API_TOKEN}"
    board_id: "${TRELLO_BOARD_ID}"
    list_id_urgent: "${TRELLO_LIST_URGENT}"
    list_id_normal: "${TRELLO_LIST_NORMAL}"
    
  claude:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-sonnet-4-20250514"
    max_tokens: 1000
    
  remotelock:
    api_key: "${REMOTELOCK_API_KEY}"
    
  email:
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_user: "${EMAIL_USER}"
    smtp_password: "${EMAIL_PASSWORD}"
    imap_host: "imap.gmail.com"
    imap_port: 993
```

### 5.4 Core Processing Logic (Webhook-Based)

```python
# api/webhooks.py

from fastapi import FastAPI, Request, HTTPException
from loguru import logger
from models.request import Request as RequestModel, RequestStatus
from ai.client import AIClient
from communication.cleaner_email import send_cleaner_query
from integrations.trello_client import create_task
from business_logic.escalation import should_escalate
from adapters.smoobu import SmoobuClient

app = FastAPI()

class WebhookHandler:
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.ai = AIClient(config.integrations.claude.api_key)
        self.smoobu = SmoobuClient(config.integrations.smoobu.api_key)
    
    async def handle_smoobu_webhook(self, payload: dict):
        """Handle incoming Smoobu webhook events"""
        action = payload.get("action")
        
        if action == "newMessage":
            await self._handle_new_message(payload)
        elif action in ["newReservation", "updateReservation"]:
            logger.info(f"Received {action} event - monitoring for future features")
        
        return {"status": "ok"}
    
    async def _handle_new_message(self, payload: dict):
        """Process new message webhook"""
        message_id = payload["data"]["id"]
        booking_id = payload["data"]["booking"]["id"]
        sender = payload["data"]["sender"]
        
        # Only process guest messages (ignore host messages)
        if sender != "guest":
            logger.debug(f"Ignoring non-guest message {message_id}")
            return
        
        logger.info(f"Processing new guest message {message_id} for booking {booking_id}")
        
        # Fetch full message and booking details from Smoobu API
        messages = await self.smoobu.get_reservation_messages(booking_id)
        booking = await self.smoobu.get_booking(booking_id)
        
        # Get the latest message
        latest_message = messages[-1]
        
        # Create message object with full context
        message = {
            "id": message_id,
            "source": "smoobu",
            "property_id": booking["apartment"]["id"],
            "property_name": booking["apartment"]["name"],
            "guest_name": booking["guest-name"],
            "guest_email": booking.get("email"),
            "booking_id": booking_id,
            "check_in": booking["arrival"],
            "check_out": booking["departure"],
            "message_text": latest_message["message"],
            "timestamp": latest_message["created-at"],
            "webhook_received_at": datetime.utcnow()
        }
        
        # Process through AI system
        await self._process_new_message(message)
    
    async def _process_new_message(self, message):
        """Main entry point for processing guest messages"""
        logger.info(f"Analyzing message from {message['guest_name']}")
        
        # Step 1: AI analyzes the message
        analysis = await self.ai.analyze_message(message["message_text"], message)
        
        if not analysis.is_checkin_request:
            logger.info(f"Message is not a check-in/out request, skipping")
            return
        
        # Step 2: Create request record
        request = RequestModel(
            source=message["source"],
            property_id=message["property_id"],
            guest_name=message["guest_name"],
            booking_id=message["booking_id"],
            original_checkin=message["check_in"],
            requested_checkin=analysis.requested_checkin,
            request_type=analysis.request_type,
            status=RequestStatus.NEW,
            urgency=self._calculate_urgency(analysis.requested_checkin),
            ai_confidence=analysis.confidence
        )
        self.db.add(request)
        self.db.commit()
        
        # Step 3: Check for immediate escalation
        if should_escalate(request, analysis):
            logger.warning(f"Request {request.id} requires escalation")
            await self._escalate_to_human(request, analysis, reason="urgent_or_low_confidence")
            return
        
        # Step 4: Query cleaning staff
        request.status = RequestStatus.PENDING_CLEANER
        self.db.commit()
        
        await send_cleaner_query(
            request=request,
            property=self._get_property(request.property_id),
            config=self.config
        )
        
        logger.info(f"Cleaner query sent for request {request.id}")
        
        # Step 5: Schedule timeout check
        self._schedule_timeout_check(request)
    
    # ... rest of the methods (same as before)

# FastAPI webhook endpoint
@app.post("/webhook/smoobu")
async def smoobu_webhook(request: Request):
    """Smoobu webhook endpoint"""
    try:
        payload = await request.json()
        
        # Validate webhook signature if configured
        if config.integrations.smoobu.webhook_secret:
            validate_webhook_signature(request.headers, payload)
        
        handler = WebhookHandler(config, db_session)
        await handler.handle_smoobu_webhook(payload)
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
```
    
    async def process_cleaner_response(self, email_message, request_id):
        """Process response from cleaning staff"""
        request = self.db.query(Request).filter_by(id=request_id).first()
        
        if not request:
            logger.error(f"Request {request_id} not found")
            return
        
        # Parse cleaner response with AI
        response_analysis = await self.ai.parse_cleaner_response(email_message.text)
        
        # Save response
        from models.message import CleanerResponse
        cleaner_response = CleanerResponse(
            request_id=request.id,
            cleaner_email=email_message.from_email,
            response=response_analysis.decision,  # 'yes', 'no', 'maybe'
            raw_message=email_message.text,
            received_at=datetime.utcnow()
        )
        self.db.add(cleaner_response)
        
        # Check if response is clear
        if response_analysis.decision == 'maybe' or response_analysis.confidence < 0.8:
            logger.warning(f"Cleaner response for {request.id} is unclear")
            await self._escalate_to_human(
                request, 
                response_analysis, 
                reason="unclear_cleaner_response"
            )
            return
        
        # Update request status
        if response_analysis.decision == 'yes':
            request.status = RequestStatus.APPROVED
            
            # Check auto-approval criteria
            if self._can_auto_approve(request):
                await self._auto_approve_and_send(request)
            else:
                await self._create_approval_task(request, response_analysis)
        else:
            request.status = RequestStatus.DENIED
            await self._create_approval_task(request, response_analysis)
        
        self.db.commit()
    
    def _calculate_urgency(self, checkin_time):
        """Calculate urgency based on time until check-in"""
        hours_until = (checkin_time - datetime.utcnow()).total_seconds() / 3600
        
        if hours_until < self.config.escalation.critical_threshold_hours:
            return "critical"
        elif hours_until < self.config.escalation.urgent_threshold_hours:
            return "urgent"
        else:
            return "normal"
    
    def _can_auto_approve(self, request):
        """Check if request meets auto-approval criteria"""
        if not self.config.auto_approval.enabled:
            return False
        
        property_config = self._get_property(request.property_id)
        if not property_config.auto_approval_enabled:
            return False
        
        hours_until = (request.requested_checkin - datetime.utcnow()).total_seconds() / 3600
        if hours_until < self.config.auto_approval.min_advance_hours:
            return False
        
        # Check if requested time is within allowed range
        requested_time = request.requested_checkin.time()
        allowed_start = datetime.strptime(self.config.auto_approval.allowed_checkin_range.earliest, "%H:%M").time()
        allowed_end = datetime.strptime(self.config.auto_approval.allowed_checkin_range.latest, "%H:%M").time()
        
        if not (allowed_start <= requested_time <= allowed_end):
            return False
        
        return True
    
    async def _auto_approve_and_send(self, request):
        """Automatically approve and send response to guest"""
        logger.info(f"Auto-approving request {request.id}")
        
        # Generate door code
        from integrations.door_lock import generate_code
        door_code = await generate_code(
            property_id=request.property_id,
            start_time=request.requested_checkin,
            end_time=request.original_checkout
        )
        
        # Generate guest response
        response_text = await self.ai.generate_guest_response(
            request=request,
            approved=True,
            door_code=door_code
        )
        
        # Send response
        from communication.guest_response import send_guest_response
        await send_guest_response(
            booking_id=request.booking_id,
            message=response_text
        )
        
        request.status = RequestStatus.SENT
        self.db.commit()
        
        logger.success(f"Request {request.id} auto-approved and sent")
    
    async def _create_approval_task(self, request, analysis):
        """Create Trello task for human approval"""
        logger.info(f"Creating approval task for request {request.id}")
        
        # Draft response
        response_text = await self.ai.generate_guest_response(
            request=request,
            approved=(request.status == RequestStatus.APPROVED)
        )
        
        # Create Trello card
        await create_task(
            request=request,
            analysis=analysis,
            drafted_response=response_text,
            config=self.config
        )
        
        request.status = RequestStatus.PENDING_APPROVAL
        self.db.commit()
    
    async def _escalate_to_human(self, request, analysis, reason):
        """Escalate request to human for manual handling"""
        logger.warning(f"Escalating request {request.id}: {reason}")
        
        await create_task(
            request=request,
            analysis=analysis,
            escalation_reason=reason,
            priority="urgent" if request.urgency in ["urgent", "critical"] else "normal",
            config=self.config
        )
        
        request.status = RequestStatus.ESCALATED
        self.db.commit()
        
        # Send notification for critical cases
        if request.urgency == "critical":
            from communication.notifications import send_sms
            await send_sms(
                phone=self.config.notifications.manager_sms,
                message=f"CRITICAL: {request.guest_name} - {reason}"
            )
```

### 5.5 AI Prompt Templates

```python
# ai/prompts.py

ANALYZE_MESSAGE_PROMPT = """
You are analyzing a message from an Airbnb guest to determine if it contains a check-in or check-out time change request.

GUEST MESSAGE:
{message_text}

BOOKING DETAILS:
- Property: {property_name}
- Current check-in: {current_checkin}
- Current check-out: {current_checkout}

Analyze the message and respond in JSON format:

{{
  "is_checkin_request": boolean,
  "request_type": "early_checkin" | "late_checkout" | "both" | null,
  "requested_checkin": "YYYY-MM-DD HH:MM" | null,
  "requested_checkout": "YYYY-MM-DD HH:MM" | null,
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation",
  "additional_requests": ["list", "of", "other", "questions"],
  "urgency_indicators": ["same-day", "emergency", etc]
}}

Be conservative: only set is_checkin_request=true if you're confident.
"""

PARSE_CLEANER_RESPONSE_PROMPT = """
Parse this email response from cleaning staff:

EMAIL:
{email_text}

ORIGINAL QUESTION:
Can cleaning be completed by {requested_time} on {date}?

Respond in JSON:
{{
  "decision": "yes" | "no" | "maybe",
  "confidence": 0.0-1.0,
  "reasoning": "Why this decision",
  "conditions": ["any", "conditions", "mentioned"],
  "alternative_time": "HH:MM" | null
}}

Look for affirmative words (yes, ok, sure, no problem) vs negative (no, can't, impossible) vs uncertain (maybe, depends).
"""

GENERATE_GUEST_RESPONSE_PROMPT = """
Generate a friendly response to the guest based on this request:

REQUEST DETAILS:
- Guest name: {guest_name}
- Request: {request_type}
- Original time: {original_time}
- Requested time: {requested_time}
- Decision: {approved}
- Door code: {door_code}

Generate a warm, professional message that:
1. Addresses the guest by name
2. Clearly states whether request is approved/denied
3. Provides the new door code if approved
4. Is friendly and welcoming
5. Is concise (2-3 sentences)

Response:
"""
```

### 5.6 Deployment Instructions

```bash
# On your VPS or local server

# 1. Clone/upload project
git clone <your-repo>
cd airbnb-automation

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
nano .env  # Add your API keys

# 5. Initialize database
alembic upgrade head

# 6. Test configuration
python main.py --test-config

# 7. Run in background with systemd
sudo cp deployment/airbnb-automation.service /etc/systemd/system/
sudo systemctl enable airbnb-automation
sudo systemctl start airbnb-automation

# 8. Check logs
sudo journalctl -u airbnb-automation -f

# 9. Set up reverse proxy (nginx) for webhook endpoint
# Your webhook URL will be: https://yourdomain.com/webhook/smoobu
```

---

## 7. Recommended Code & Documentation Repository Structure

### 7.1 Git Repository Organization

I recommend using **Git** with the following structure:

```
Repository: airbnb-checkin-automation/
│
├── .git/
├── .github/                    # GitHub-specific (if using GitHub)
│   └── workflows/              # CI/CD pipelines (optional)
│       └── tests.yml
│
├── README.md                   # Project overview, quick start
├── LICENSE                     # MIT or your choice
├── .gitignore                  # Python, environment files, data/
├── requirements.txt
├── requirements-dev.txt        # Dev dependencies (pytest, black, etc.)
├── .env.example               # Template for environment variables
│
├── docs/                      # All documentation here
│   ├── ARCHITECTURE.md        # This document
│   ├── SETUP.md              # Detailed setup instructions
│   ├── API_INTEGRATION.md    # Smoobu integration guide
│   ├── DEPLOYMENT.md         # Deployment to VPS/cloud
│   ├── TROUBLESHOOTING.md    # Common issues and solutions
│   └── api-specs/            # External API documentation
│       ├── smoobu/
│       │   ├── README.md     # Link to https://docs.smoobu.com
│       │   ├── webhooks.md   # Webhook events reference
│       │   └── endpoints.md  # Key API endpoints
│       ├── trello/
│       │   └── README.md     # Link to Trello API docs
│       └── remotelock/
│           └── README.md
│
├── src/                       # All application code
│   ├── main.py
│   ├── api/
│   ├── adapters/
│   ├── ai/
│   └── ... (rest of code structure)
│
├── tests/
├── migrations/
├── deployment/                # Deployment configs
│   ├── systemd/
│   │   └── airbnb-automation.service
│   ├── nginx/
│   │   └── airbnb-automation.conf
│   └── docker/
│       ├── Dockerfile
│       └── docker-compose.yml
│
└── data/                     # Gitignored - runtime data
    ├── .gitkeep
    ├── database.db
    └── logs/
```

### 7.2 Where to Store What

**Code Storage Options:**

1. **GitHub** (Recommended)
   - ✅ Free private repositories
   - ✅ Good for collaboration
   - ✅ CI/CD integration (GitHub Actions)
   - ✅ Issue tracking
   - URL: `https://github.com/yourusername/airbnb-checkin-automation`

2. **GitLab**
   - ✅ Free private repos with CI/CD included
   - ✅ Self-hosting option available
   - Good alternative to GitHub

3. **Self-hosted Git** (Gitea/Gogs)
   - ✅ Full control
   - ✅ Can run on same VPS
   - More setup required

**Documentation Storage:**

1. **Inside Repository** (`docs/` folder) ✅ Recommended
   - Version controlled with code
   - Easy to keep in sync
   - Markdown renders nicely on GitHub/GitLab
   - **Store**: Architecture, API integration guides, setup instructions

2. **External API Specs** (reference by link)
   - Smoobu: https://docs.smoobu.com (keep link in `docs/api-specs/smoobu/README.md`)
   - Trello: https://developer.atlassian.com/cloud/trello/
   - Don't duplicate external docs, just reference them

3. **Optional: Wiki** (GitHub/GitLab Wiki)
   - For more extensive documentation
   - Easier to edit without commits
   - Good for runbooks, FAQs

**Sensitive Data (Never commit!):**

- API keys → Environment variables (`.env` file, gitignored)
- Database → `data/` directory (gitignored)
- Logs → `data/logs/` (gitignored)
- Config with secrets → Use `.env.example` as template

### 7.3 .gitignore Template

```gitignore
# Environment
.env
.env.local
venv/
env/
ENV/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/

# Database
data/
*.db
*.sqlite
*.sqlite3

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Build
dist/
build/
```

### 7.4 Recommended Workflow

```bash
# 1. Initialize repository
git init
git remote add origin https://github.com/yourusername/airbnb-checkin-automation.git

# 2. Initial commit
git add .
git commit -m "Initial project structure"
git push -u origin main

# 3. Create development branch
git checkout -b develop

# 4. Work on features
git checkout -b feature/smoobu-webhook
# ... make changes ...
git add .
git commit -m "Add Smoobu webhook handler"
git push origin feature/smoobu-webhook

# 5. Merge to develop, then to main for releases
git checkout develop
git merge feature/smoobu-webhook
git checkout main
git merge develop --no-ff
git tag -a v0.1.0 -m "First working version"
git push origin main --tags
```

### 7.5 Documentation Best Practices

1. **Keep docs close to code**: All docs in repository
2. **Use Markdown**: GitHub/GitLab render it beautifully
3. **Link external APIs**: Don't copy, just reference
4. **Update with code**: Documentation changes in same commit
5. **Examples over theory**: Show code snippets, not just descriptions
6. **Changelog**: Maintain a CHANGELOG.md for version history

---

## 8. Function List

### 8.1 Core Functions

1. **Message Ingestion**
   - `fetch_new_smoobu_messages()`: Poll Smoobu API for new messages
   - `handle_smoobu_webhook(payload)`: Process incoming webhook
   - `normalize_message(raw_message)`: Convert to standard format

2. **AI Processing**
   - `analyze_guest_message(text)`: Detect and extract request details
   - `parse_cleaner_response(email)`: Understand cleaner's answer
   - `generate_guest_reply(request, approved, code)`: Draft response
   - `calculate_confidence(analysis)`: Assess AI certainty

3. **Cleaning Staff Communication**
   - `send_cleaner_email(request, template)`: Send query via email
   - `poll_cleaner_inbox()`: Check for responses
   - `match_response_to_request(email)`: Thread tracking

4. **Guest Response**
   - `send_guest_message(booking_id, text)`: Send via Smoobu
   - `format_response(template, data)`: Personalize message

5. **Task Management**
   - `create_trello_card(request, priority, details)`: Make task
   - `update_task_status(card_id, status)`: Update progress
   - `check_task_completion()`: Monitor for approvals

6. **Door Code Management**
   - `generate_door_code(property, start, end)`: Create code
   - `update_code_validity(code, new_times)`: Modify existing
   - `revoke_code(code_id)`: Cancel code

7. **Business Logic**
   - `should_escalate(request, analysis)`: Apply escalation rules
   - `calculate_urgency(checkin_time)`: Determine priority
   - `can_auto_approve(request)`: Check auto-approval criteria
   - `handle_timeout(request_id)`: Process cleaner timeout

8. **State Management**
   - `update_request_status(id, new_status)`: State transitions
   - `get_pending_requests()`: Query active requests
   - `cleanup_old_requests()`: Archive completed

---

## 9. Development Roadmap

### Phase 1: MVP (Weeks 1-3)
- [x] Database schema
- [ ] Smoobu webhook endpoint
- [ ] AI integration (Claude API)
- [ ] Email communication with cleaners
- [ ] Basic Trello task creation
- [ ] Manual testing with real scenarios

### Phase 2: Core Features (Weeks 4-6)
- [ ] Escalation logic implementation
- [ ] Timeout handling
- [ ] Door code integration (RemoteLock)
- [ ] Auto-approval logic
- [ ] Logging and monitoring

### Phase 3: Reliability (Weeks 7-8)
- [ ] Error handling and retries
- [ ] Unit tests for core logic
- [ ] Integration tests for scenarios
- [ ] Deployment scripts
- [ ] Documentation

### Phase 4: Enhancements (Weeks 9-12)
- [ ] Web dashboard for monitoring
- [ ] Analytics and reporting
- [ ] Multi-language support
- [ ] WhatsApp integration option
- [ ] Mobile notifications

---

## 10. Monitoring & Maintenance

### 10.1 Key Metrics

- **Processing Time**: Time from guest message to cleaner query
- **Response Rate**: % of cleaner responses within timeout
- **Auto-Approval Rate**: % of requests auto-approved
- **Escalation Rate**: % of requests requiring human intervention
- **Error Rate**: Failed API calls, timeouts, etc.

### 10.2 Logging

```python
# All important events should be logged

logger.info(f"New message received: {message_id}")
logger.debug(f"AI analysis: {analysis}")
logger.warning(f"Cleaner timeout: {request_id}")
logger.error(f"Failed to send email: {error}")
logger.success(f"Request completed: {request_id}")
```

### 10.3 Alerts

Set up alerts for:
- Multiple consecutive failures
- Escalation rate > 50%
- Any critical request not handled within 1 hour
- Database connection failures

---

## Appendix A: API Integrations Reference

### Smoobu API
- Docs: https://www.smoobu.com/en/api/
- Messages endpoint: `GET /api/messages`
- Send message: `POST /api/messages/{bookingId}`

### Trello API
- Docs: https://developer.atlassian.com/cloud/trello/
- Create card: `POST /1/cards`
- Update card: `PUT /1/cards/{id}`

### RemoteLock API
- Docs: https://docs.remotelock.com/
- Create code: `POST /access_codes`
- Update code: `PUT /access_codes/{id}`

### Claude API
- Docs: https://docs.anthropic.com/
- Messages: `POST /v1/messages`
- Model: `claude-sonnet-4-20250514`

---

## Appendix A: API References & Documentation Links

### Smoobu API
- **Primary Documentation**: https://docs.smoobu.com
- **Authentication**: API Key (found in: Advanced > API Keys)
- **Base URL**: `https://login.smoobu.com/api/`
- **Webhook Configuration**: Advanced > API Keys > Webhook URLs
- **Note**: Smoobu does not provide an OpenAPI/Swagger specification file. Documentation is web-based using Slate framework.

**Key Endpoints for This Project**:
```
GET  /reservations/{id}/messages          # Fetch conversation history
POST /reservations/{id}/messages          # Send message to guest
GET  /reservations/{id}                   # Get booking details
GET  /apartments                          # List properties
```

**Webhook Events**:
- `newMessage` - New message from guest
- `newReservation` - New booking created
- `updateReservation` - Booking modified
- `cancelReservation` - Booking cancelled

### Trello API
- **Documentation**: https://developer.atlassian.com/cloud/trello/
- **REST API Reference**: https://developer.atlassian.com/cloud/trello/rest/
- **Authentication**: API Key + Token
- **Rate Limits**: 100 requests per 10 seconds per token

### RemoteLock API
- **Documentation**: https://docs.remotelock.com/
- **Authentication**: OAuth 2.0
- **Base URL**: `https://api.remotelock.com/`

### Claude AI API (Anthropic)
- **Documentation**: https://docs.anthropic.com/
- **API Reference**: https://docs.anthropic.com/en/api
- **Model**: `claude-sonnet-4-20250514`
- **Rate Limits**: Varies by plan

---

**End of Document**
