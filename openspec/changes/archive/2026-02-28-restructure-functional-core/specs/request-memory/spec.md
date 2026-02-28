## MODIFIED Requirements

### Requirement: Port location
RequestMemory ABC and its data types (ProcessedRequest, Draft) SHALL be defined in `src/ports/memory.py`. No behavioral changes.

#### Scenario: Import path updated
- **WHEN** code imports RequestMemory, ProcessedRequest, or Draft
- **THEN** the import SHALL be from `src.ports.memory`
