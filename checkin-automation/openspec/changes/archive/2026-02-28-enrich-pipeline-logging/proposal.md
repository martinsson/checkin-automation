## Why

The pipeline is entirely silent. Every meaningful step — intent classification, draft creation,
cleaner response parsing — happens without any log output. The only feedback visible to the operator
is the single-line action string emitted by the daemon after `process_message()` returns. This
makes it impossible to diagnose issues without adding temporary print statements.

Specifically, the following information is currently invisible in logs:

- Which intent was classified (and with what confidence and extracted time)
- Whether the dedup guard fired (message already seen vs. intent already processed)
- Which draft IDs were saved for each step
- What cleaner response was parsed (yes/no/conditional/unclear) and what reply was composed

## What Changes

Add `log.debug` / `log.info` calls at key steps inside `Pipeline.process_message()` and
`Pipeline._handle_cleaner_response()`. No new parameters, no new ports, no behaviour change —
purely instrumentation.

## Capabilities

### Modified Capabilities

- `pipeline-orchestration`: `process_message()` logs at each decision point:
  1. Entry — reservation ID, message preview, message_id
  2. Dedup guard hit — message_id already seen
  3. Classification result — intent, confidence, extracted_time
  4. Intent-level dedup hit — (reservation_id, intent) already processed
  5. Follow-up drafted — question text and draft_id
  6. Drafts created — acknowledgment draft_id + cleaner_query draft_id

  `_handle_cleaner_response()` logs:
  1. Entry — request_id
  2. Parsed response — verdict (yes/no/conditional/unclear)
  3. Guest reply drafted — draft_id and body preview

## Impact

- No behaviour change, no schema change, no new dependencies.
- Log lines use `log.debug` for verbose detail (classification internals) and `log.info` for
  actions that produce output (draft saved, dedup fired, response parsed).
- Operators running with `DEBUG` level see everything; `INFO` level shows the meaningful outcomes.
