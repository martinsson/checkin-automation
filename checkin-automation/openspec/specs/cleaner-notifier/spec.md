## MODIFIED Requirements

### Requirement: Port location
CleanerNotifier ABC and its data types (CleanerQuery, CleanerResponse) SHALL be defined in `src/ports/cleaner.py`. No behavioral changes.

#### Scenario: Import path updated
- **WHEN** code imports CleanerNotifier, CleanerQuery, or CleanerResponse
- **THEN** the import SHALL be from `src.ports.cleaner`
