# Integrations — the coordination hub

This is the no-code half of the repo: how the rental tech stack fits together, the
account/config IDs that matter, and where each piece lives. The Python automation app is a
separate module in [`../checkin-automation/`](../checkin-automation/).

> **Conventions for these docs:** keep them lean. State *what a tool does for us*, the
> IDs/hooks needed to find things, and **link** to the canonical source rather than copying
> it. Credentials are never written here — they live centrally at the repo root and are
> catalogued in [`../secrets/access-map.md`](../secrets/access-map.md) (gitignored).

## Properties

Six listings: **La Palma, Le Fernand, Le Matisse, Studio Écrin, Terracotta, Velours T2.**

## Tools

| Tool | Role in the stack | Doc |
|------|-------------------|-----|
| **Smoobu** | Channel manager + guest messaging; source of reservations & message threads. Drives the automation app. | [smoobu/](smoobu/) |
| **Beds24** | Owns guest messaging automation (auto actions) and door-code delivery. | [beds24/](beds24/) |
| **igloohome** | Smart locks (Keybox 3 + Retrofit); generates the PINs. | [igloohome/](igloohome/) |
| **Make** | Glue/automation scenarios wiring Beds24 ↔ igloohome. | [make/](make/) |
| **PriceLabs** | Dynamic pricing. | [pricelabs/](pricelabs/) *(stub — TODO)* |
| **HostBuddy** | _TODO: describe._ | [hostbuddy/](hostbuddy/) *(stub — TODO)* |

## Cross-cutting flows

- **[Door codes](door-codes.md)** — Beds24 + Make + igloohome generate and deliver the
  access PIN to each guest. Spans three tools; this is the canonical write-up.

## The app

[`../checkin-automation/`](../checkin-automation/) — Python service that polls Smoobu for
guest messages, classifies intent with Claude, and orchestrates the guest↔host↔cleaner loop.
See its [README](../checkin-automation/README.md) and
[docs/ARCHITECTURE.md](../checkin-automation/docs/ARCHITECTURE.md).
