## MODIFIED Requirements

### Requirement: Port location
ReservationCache ABC SHALL be defined in `src/ports/reservation_cache.py`. No behavioral changes.

#### Scenario: Import path updated
- **WHEN** code imports ReservationCache
- **THEN** the import SHALL be from `src.ports.reservation_cache`
