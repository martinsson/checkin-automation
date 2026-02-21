## 1. Add logger to `pipeline.py`

- [x] 1.1 Add `import logging` and `log = logging.getLogger(__name__)` at the top of
  `src/pipeline.py`.

## 2. Add log calls to `Pipeline.process_message()`

- [x] 2.1 Entry log (DEBUG): message preview and message_id.
  ```
  log.debug("res=%d msg_id=%d message=%.60r", reservation_id, message_id, message)
  ```
- [x] 2.2 Dedup guard hit (INFO): when `has_message_been_seen` returns True.
  ```
  log.info("res=%d msg_id=%d skip: message already seen", reservation_id, message_id)
  ```
- [x] 2.3 Classification result (INFO): intent, confidence, extracted_time.
  ```
  log.info("res=%d msg_id=%d classified → intent=%s conf=%.2f time=%s",
           reservation_id, message_id, result.intent, result.confidence,
           result.extracted_time or "?")
  ```
- [x] 2.4 Intent-level dedup hit (INFO): when `has_been_processed` returns True.
  ```
  log.info("res=%d intent=%s skip: already processed", reservation_id, result.intent)
  ```
- [x] 2.5 Follow-up drafted (INFO): draft_id and truncated question text.
  ```
  log.info("res=%d intent=%s followup draft=%d: %.60s",
           reservation_id, result.intent, draft_id, result.followup_question)
  ```
- [x] 2.6 Drafts created (INFO): acknowledgment draft_id and cleaner_query draft_id.
  ```
  log.info("res=%d intent=%s drafts created: ack=%d cleaner_query=%d",
           reservation_id, result.intent, ack_draft_id, query_draft_id)
  ```

## 3. Add log calls to `Pipeline._handle_cleaner_response()`

- [x] 3.1 Parsed response (INFO): request_id and parsed answer.
  ```
  log.info("cleaner response req=%s parsed → %s", response.request_id, parsed.answer)
  ```
  Note: field is `ParsedResponse.answer` (not `verdict`).
- [x] 3.2 Guest reply drafted (INFO): draft_id and truncated reply body.
  ```
  log.info("cleaner response req=%s guest reply draft=%d: %.60s",
           response.request_id, reply_draft_id, reply.body)
  ```

## 4. Adjust daemon log level for classification outcome

- [x] 4.1 In `src/daemon.py`, change the post-pipeline `log.info(...)` so it no longer filters
  out `"already_processed"` and `"ignored"` — those are now informative because the pipeline
  already logged the details. Replace the condition `if result.action not in
  ("ignored", "already_processed")` with an unconditional `log.debug(...)` (since the pipeline
  now logs at INFO for those cases).
