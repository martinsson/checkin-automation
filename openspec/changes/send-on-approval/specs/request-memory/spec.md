## ADDED Requirements

### Requirement: Retrieve reviewed but unsent drafts
`RequestMemory.get_reviewed_unsent_drafts()` SHALL return all `Draft` objects where `verdict IN ('ok', 'nok')` AND `sent_at IS NULL`, ordered by `created_at` ascending.

#### Scenario: Only unsent reviewed drafts returned
- **WHEN** drafts exist with verdicts "ok", "nok", and "pending", and some have `sent_at` set
- **THEN** `get_reviewed_unsent_drafts()` SHALL return only those with a verdict AND `sent_at IS NULL`

#### Scenario: No reviewed unsent drafts
- **WHEN** all reviewed drafts have `sent_at` set
- **THEN** `get_reviewed_unsent_drafts()` SHALL return an empty list

### Requirement: Mark a draft as sent
`RequestMemory.mark_draft_sent(draft_id)` SHALL set the `sent_at` column to the current UTC timestamp for the given draft.

#### Scenario: Draft marked as sent
- **WHEN** `mark_draft_sent(draft_id)` is called
- **THEN** `get_draft(draft_id).sent_at` SHALL be non-null
- **AND** the draft SHALL no longer appear in `get_reviewed_unsent_drafts()`

### Requirement: Draft dataclass includes sent_at field
The `Draft` dataclass SHALL include a `sent_at: datetime | None` field, defaulting to `None`.

#### Scenario: New draft has sent_at=None
- **WHEN** a draft is created via `save_draft()`
- **THEN** `get_draft(draft_id).sent_at` SHALL be `None`
