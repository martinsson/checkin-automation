## MODIFIED Requirements

### Requirement: Monitor active conversations via thread-based activity scan
The guest message poller (`shell/pollers/guest_messages.py`) SHALL use `GET /api/threads` as the activity index. It SHALL paginate threads until it encounters a page where all threads have `latest_message_at` older than the cutoff. This logic moves from `poll_once()` to the dedicated poller.

#### Scenario: Thread pagination stops at cutoff
- **WHEN** a page of threads contains entries all older than the cutoff
- **THEN** pagination SHALL stop and no further pages SHALL be fetched

#### Scenario: Active threads within cutoff are processed
- **WHEN** a thread has `latest_message_at` within the cutoff window
- **THEN** the poller SHALL yield its reservation for handling

### Requirement: Process only the latest guest message per reservation per cycle
The guest message poller SHALL extract the last non-empty guest message per reservation. Earlier messages SHALL be included as `previous_messages` in the yielded context.

#### Scenario: Only last message included in yielded item
- **WHEN** a reservation has three guest messages
- **THEN** the yielded item SHALL contain the third message as the primary message
- **AND** the first two SHALL appear in `previous_messages`

### Requirement: Dispatch reviewed drafts at the end of each poll cycle
The main cycle (`shell/main_cycle.py`) SHALL call the draft dispatch handler after guest message handling and cleaner response handling.

#### Scenario: Dispatch runs after cleaner response handling
- **WHEN** a poll cycle completes guest message handling and cleaner response handling
- **THEN** draft dispatch SHALL run before the cycle ends

### Requirement: Cleaner response polling runs at the end of every poll cycle
The main cycle SHALL call the cleaner response poller and handler once per cycle, after guest message handling.

#### Scenario: Cleaner polling occurs after guest message processing
- **WHEN** a poll cycle completes guest message handling
- **THEN** cleaner response polling and handling SHALL occur before draft dispatch

## REMOVED Requirements

### Requirement: poll_once() as monolithic function
**Reason**: Replaced by `shell/main_cycle.py` which composes pollers and handlers. The thread scanning moves to the guest message poller, cleaner polling to the cleaner response poller, and dispatch to the draft dispatch handler.
**Migration**: `poll_once()` becomes `poll_cycle()` in `shell/main_cycle.py`, calling pollers then handlers then dispatch in sequence. `scripts/run.py` still owns the sleep loop.
