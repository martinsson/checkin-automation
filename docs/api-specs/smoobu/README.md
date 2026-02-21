# Smoobu API Reference

**Docs:** https://docs.smoobu.com/#introduction
**Base URL:** `https://login.smoobu.com/api`
**Auth:** `Api-Key` header

## Endpoints in use

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/reservations` | List reservations. Filters: `apartmentId`, `arrivalFrom`, `arrivalTo`, `pageSize`, `page` |
| `GET`  | `/reservations/{id}/messages` | Fetch full message thread for a reservation |
| `POST` | `/reservations/{id}/messages/send-message-to-guest` | Send a message to the guest. Body: `{ "subject": "...", "messageBody": "..." }` |

## Notes

- Reservation list is paginated (`page_count` in response).
- `arrivalFrom` / `arrivalTo` filter by **arrival** date, not departure. Guests currently staying (arrived before today) are excluded unless the window is extended backwards.
- Messages are returned under a `messages` key; each has `id`, `subject`, `message`.
