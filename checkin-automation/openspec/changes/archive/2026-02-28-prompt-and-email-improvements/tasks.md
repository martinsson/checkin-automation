## Tasks

### Cleaner email format
- [x] Update `EmailCleanerNotifier.send_query()` subject to `{property_name} — {date}` (remove `[REQ-...]` from subject)
- [x] Update `EmailCleanerNotifier.send_query()` body to use French greeting template: `Bonjour {cleaner_name},\n\nVoici une nouvelle demande...\n\n{message}\n\n[REQ-{request_id}]`
- [x] Add Claude translation call in `EmailCleanerNotifier.send_query()` to translate guest message to French before inserting into body
- [x] Update `EmailCleanerNotifier.poll_responses()` to extract request ID from `X-Request-ID` header first, then fall back to body `[REQ-...]` pattern, then subject
- [x] Update `ConsoleCleanerNotifier` to include the French template format for consistency in dev testing

### Reply composer tip simplification
- [x] Update `src/prompts/reply_composer.txt` to simplify tip mention to a single brief optional sentence

### Tests
- [x] Add test for email subject format (no REQ tag)
- [x] Add test for email body format (French template with greeting and REQ tag in body)
- [x] Add test for request ID extraction from body fallback
