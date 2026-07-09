## Design Decisions

### Decision 1: Cleaner email body is formatted in EmailCleanerNotifier, not in the pipeline

The email body template (greeting + context + translated message) is constructed in `EmailCleanerNotifier.send_query()`, not in the pipeline. The `CleanerQuery.message` field continues to carry the guest's original message. The notifier adapter is responsible for formatting it into the French template.

Rationale: The formatting is channel-specific (email vs console vs future WhatsApp). The port interface stays clean — adapters decide presentation.

### Decision 2: No new field on CleanerQuery for translation

Rather than adding a `translated_message` field to `CleanerQuery`, the email notifier formats the body using the existing fields: `cleaner_name` for the greeting and `message` for the guest text. Translation of the guest message into French happens in the email adapter using a simple Claude call, since the guest may write in any language.

Alternative considered: Adding a `translated_message` field populated by the pipeline. Rejected because translation is a presentation concern, not a domain concern.

### Decision 3: Request ID moves to X-header only

The `[REQ-...]` tag is removed from the subject line. The request ID is already in the `X-Request-ID` header (line 45 of email_notifier.py). The `poll_responses` method already uses regex on the subject to extract it — it needs to also check the `X-Request-ID` header and the body. For replies (which lose custom headers), we add `[REQ-...]` at the bottom of the body as a fallback.

### Decision 4: Tip mention is a single sentence, not a paragraph

The reply_composer prompt is simplified: instead of the current multi-sentence tip suggestion, use a single brief mention like "certains voyageurs laissent un petit pourboire, c'est tout à fait optionnel". Keep it natural and short.
