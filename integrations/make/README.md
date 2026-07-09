# Make (make.com)

**Role:** Automation glue between [Beds24](../beds24/) and [igloohome](../igloohome/) —
turns a booking into an igloohome PIN and writes it back to the booking.

**Account / access:** see [`../../secrets/access-map.md`](../../secrets/access-map.md).

## Scenarios

| Scenario | Webhook | What it does |
|----------|---------|--------------|
| **5738113** | `hook.eu1.make.com/xohk7…` | Receives booking id + dates + lock device id from Beds24 auto action 586004, generates the igloohome PIN, and writes it back to the booking as the `IGLOOPIN` booking-info code. |

## See also

- **[Door codes](../door-codes.md)** — the end-to-end flow this scenario sits in the middle of.
