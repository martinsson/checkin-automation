# checking-automation

The **coordination hub** for a short-term-rental tech stack — six listings across Smoobu,
Beds24, igloohome, Make, PriceLabs, and HostBuddy — plus the Python service that automates
guest messaging.

## Layout

| Path | What's there |
|------|--------------|
| **[`integrations/`](integrations/)** | No-code coordination knowledge: one folder per tool, how they fit together, the account/config IDs. **Start here** for "how does X work / where is it configured". |
| **[`checkin-automation/`](checkin-automation/)** | The Python app — polls Smoobu, classifies guest intent with Claude, orchestrates the guest ↔ host ↔ cleaner loop. Self-contained; run/test from inside it. |
| **`secrets/`** | Central credentials (gitignored). [`secrets/access-map.md`](secrets/access-map.md) catalogues which account/key each tool needs and where it lives. |
| **`.env` / `.env.example`** | Central runtime config for the app (gitignored / template). |
| **[`CLAUDE.md`](CLAUDE.md)** | Business intent, invariants, and architecture notes. |

The two modules are deliberately separable — a future split into two repos should be a clean
`git mv`.

## Quick start

**Coordinating the tools (no code):** browse [`integrations/`](integrations/). Cross-tool
flows like [door codes](integrations/door-codes.md) are documented there.

**Running the app:**

```bash
cd checkin-automation
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then fill in credentials (see ../secrets/access-map.md)
make test                    # network-free unit + simulator tests
make run                     # poll Smoobu and process guest messages
```

See [`checkin-automation/README.md`](checkin-automation/README.md) and
[`checkin-automation/docs/ARCHITECTURE.md`](checkin-automation/docs/ARCHITECTURE.md) for detail.
