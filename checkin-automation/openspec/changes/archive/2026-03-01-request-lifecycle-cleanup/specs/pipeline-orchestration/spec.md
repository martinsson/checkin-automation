## REMOVED Requirements

### Requirement: Followup draft handling in guest request handler
**Reason**: The followup path is removed. The handler no longer creates followup drafts or returns `followup_drafted`.
**Migration**: Remove the `isinstance(result, Followup)` branch from `src/shell/handlers/guest_request.py`. The handler only handles `Skip` and `Actionable` results.
