# Smoobu

**Role:** Channel manager and guest-messaging platform. It is the source of truth for
reservations and guest message threads, and the channel the automation app uses to
acknowledge guests.

**Account / access:** see [`../../secrets/access-map.md`](../../secrets/access-map.md)
(`SMOOBU_API_KEY`, `SMOOBU_APARTMENT_ID`, `SMOOBU_WEBHOOK_SECRET`).

## What we use it for

- The [`checkin-automation`](../../checkin-automation/) app polls `/reservations` and
  `/reservations/{id}/messages`, classifies guest intent, and posts acknowledgements via
  `send-message-to-guest`.
- Guest messaging *automation* (templates, door codes) is **not** here — that's in
  [Beds24](../beds24/).

## Reference

- **API endpoints, auth, and known quirks:** [`api-specs/README.md`](api-specs/README.md)
  (e.g. the `arrivalFrom` filter excludes guests currently staying).
- **Official docs:** https://docs.smoobu.com/#introduction
- **Code:** `../../checkin-automation/src/adapters/` (Smoobu gateway) and
  `src/ports/` (the gateway contract).
