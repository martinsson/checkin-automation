# Beds24

**Role:** Owns guest-messaging automation and door-code delivery for all six properties.
This is where auto actions, templates, and access instructions live — **not** in the Python
app, and not in Smoobu.

**Account / access:** account **162463** (`martinsson.rouveyrol`). Secrets →
[`../../secrets/access-map.md`](../../secrets/access-map.md).

## Guest messaging (Auto Actions)

Configured under **Guest Management → Auto Actions**.

- **586256 — "Send igloohome PIN to guest"** — fires on check-in. Sends the code via
  `[BOOKINGINFOCODETEXT:IGLOOPIN]`. Targets all rooms owned by the account **except
  662419 / 662418** (Velours T2 + Studio Écrin).
- **Velours T2 & Studio Écrin** deliver their code via **igloohome's iglooConnect↔Airbnb**
  integration instead (hence the exclusion). They also have "Bevière vidéo" access actions
  (**590557, 590565**) that send only a YouTube walkthrough link.
- **582702 — general access-info email** — uses `[PROPERTYTEMPLATE1/2]`.

## Template conventions

- Per-language: `[PROPERTYTEMPLATE1]` = **French**, `[PROPERTYTEMPLATE2]` = **English**.
- **All 8 Property Template slots are full** (T1/2 access info FR/EN, T3/4 key-return,
  T5/6 smoking notice, T7 a code, T8 = igloohome Keybox device id, e.g. `IGK343002588`).
  Use **Room Templates** for any new per-property text (each property has a single room).

## Locks

Two lock types (see [igloohome](../igloohome/)):
- **Keybox 3:** Terracotta, La Palma, Velours T2, Studio Écrin.
- **Retrofit Lock:** Le Matisse, Le Fernand.

## See also

- **[Door codes](../door-codes.md)** — the full Beds24 → Make → igloohome generation/delivery flow.
- Minor duplication between the code message and access-info templates is acceptable —
  no need to meticulously dedupe.
