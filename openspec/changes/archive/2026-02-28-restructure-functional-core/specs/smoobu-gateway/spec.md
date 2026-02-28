## MODIFIED Requirements

### Requirement: Port location
SmoobuGateway ABC and its data types (GuestMessage, ActiveReservation, Thread, ThreadPage, ReservationInfo) SHALL be defined in `src/ports/smoobu.py`. No behavioral changes.

#### Scenario: Import path updated
- **WHEN** code imports SmoobuGateway or its data types
- **THEN** the import SHALL be from `src.ports.smoobu`
