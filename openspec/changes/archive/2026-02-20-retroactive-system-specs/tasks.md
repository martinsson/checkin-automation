## 1. Spec Authoring (retroactive)

- [x] 1.1 Write proposal identifying all 7 capabilities to specify
- [x] 1.2 Write design.md capturing architectural decisions and open questions
- [x] 1.3 Write spec: `intent-classification` — ConversationContext, ClassificationResult, follow-up logic, simulator contract
- [x] 1.4 Write spec: `response-parsing` — ParsedResponse, ComposedReply, GuestAcknowledger, ReplyComposer contracts
- [x] 1.5 Write spec: `request-memory` — idempotency, draft lifecycle, owner review, SQLite in-memory requirement
- [x] 1.6 Write spec: `smoobu-gateway` — get_messages, send_message, get_active_reservations, simulator state
- [x] 1.7 Write spec: `cleaner-notifier` — send_query, poll_responses, no-duplicate guarantee, console adapter
- [x] 1.8 Write spec: `pipeline-orchestration` — intent→idempotency→drafts flow, no-direct-send invariant
- [x] 1.9 Write spec: `daemon-runner` — poll loop, look-ahead window, last-message-only rule, error isolation

## 2. Fix Known Issues Found During Spec Authoring

- [x] 2.1 Remove hardcoded cleaner name `"Marie"` from `pipeline.py:118` — load from config or `ConversationContext`
- [x] 2.2 Fix stub `CleanerQuery` in `Pipeline._handle_cleaner_response()` — populate `guest_name`, `property_name`, `original_time`, `requested_time` from the stored `ProcessedRequest` instead of hardcoded values
- [x] 2.3 Add `cleaner_name` and `property_name` fields to `ActiveReservation` or a config object so the pipeline can build a complete `CleanerQuery` without stubs

## 3. Test Coverage Alignment

- [x] 3.1 Verify `test_memory_contract.py` covers: `has_been_processed` returning `False` for different intents on same reservation
- [x] 3.2 Verify `test_smoobu_contract.py` covers: `send_message()` output appears in subsequent `get_messages()` call
- [x] 3.3 Verify `test_cleaner_contract.py` covers: response not returned twice after `poll_responses()`
- [x] 3.4 Verify `test_pipeline.py` covers: `needs_followup=True` path returns `action="followup_drafted"` with no `cleaner_query` draft
- [x] 3.5 Verify `test_pipeline.py` covers: two different intents for the same reservation are processed independently

## 4. Archive Specs to Main Spec Store

- [x] 4.1 Run `openspec verify --change retroactive-system-specs` to confirm all spec scenarios have test coverage
- [ ] 4.2 Archive change: `openspec archive --change retroactive-system-specs` to promote specs to `openspec/specs/`
