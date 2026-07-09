## Why

The current prompts and email formats have several rough edges identified from production use: the cleaner email is impersonal and includes the raw guest message (often in English) without context; the tip suggestion in the guest reply is awkward; the request ID clutters the email subject line; and early check-in classification doesn't distinguish between luggage drop-off and actual entry, leading to unnecessary cleaner queries.

## What Changes

- **Cleaner email body**: Replace the raw guest message with a polite French template: greeting with cleaner name, context sentence, and the guest's message translated into French.
- **Tip suggestion**: Simplify — remove the elaborate tip paragraph from the reply composer prompt, keep it to a brief optional mention.
- **Request ID in email**: Move `[REQ-...]` from the subject line to the email body (or an X-header). The subject should be human-friendly: just property name and date.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cleaner-notifier`: Change the email body format to use a French greeting template with translated guest message
- `response-parsing`: Simplify the tip suggestion in reply_composer prompt

## Impact

- `src/prompts/reply_composer.txt` — simplified tip mention
- `src/communication/email_notifier.py` — restructured email body and subject
