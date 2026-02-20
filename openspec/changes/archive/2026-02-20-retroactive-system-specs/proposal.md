## Why

The checking-automation system has been implemented without formal OpenSpec specifications, leaving the architecture, contracts, and requirements undocumented in structured form. Retroactively creating these specs provides a canonical reference for the port/adapter contracts, domain model invariants, and pipeline behaviour — enabling future contributors to understand what is required (not just what was built) and to validate that simulator adapters correctly satisfy the same contracts as real adapters.

## What Changes

- Add specification files for all core capabilities of the system as it exists today
- No code changes — specs reflect the implemented behaviour derived from source, ARCHITECTURE.md, PLAN.md, and the test suite
- Establish `openspec/specs/` as the authoritative contract layer for ports, domain models, and pipeline rules

## Capabilities

### New Capabilities

- `intent-classification`: Contract and rules for classifying guest messages into `early_checkin`, `late_checkout`, or `other`, including `ConversationContext` inputs, `ClassificationResult` outputs, confidence thresholds, time extraction, and follow-up logic
- `response-parsing`: Contract for parsing cleaner free-text replies into structured `ParsedResponse` (yes/no/conditional/unclear) and composing friendly `ComposedReply` messages for guests
- `request-memory`: Spec for the `RequestMemory` port — idempotent request tracking, draft lifecycle (pending → reviewed), owner feedback recording, and the SQLite schema backing the default implementation
- `smoobu-gateway`: Contract for the `SmoobuGateway` port — fetching guest messages, sending messages, and listing active reservations; including the simulator adapter behaviour
- `cleaner-notifier`: Contract for the `CleanerNotifier` port — sending structured queries to cleaning staff and polling for their replies; including console and email adapter behaviour
- `pipeline-orchestration`: Rules governing the end-to-end message-processing pipeline: intent detection → idempotency check → draft creation → owner review → cleaner query → response parsing → guest reply drafting
- `daemon-runner`: Spec for the polling daemon: reservation look-ahead window, poll interval, ordered processing of guest messages and cleaner responses, error isolation per reservation

### Modified Capabilities

*(none — no existing specs exist; all are new)*

## Impact

- **No code changes** — purely documentation
- New files under `openspec/specs/<capability>/spec.md`
- Provides the base layer for future delta specs when requirements evolve
- Enables `openspec-verify-change` to validate simulator adapters against port contracts
