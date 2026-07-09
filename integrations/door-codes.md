# Door codes (managed in Beds24, not this repo)

Door-code generation and delivery live entirely in Beds24 + igloohome, outside this codebase:

1. Beds24 auto action **586004 "create igloohome code"** (no message; fires a webhook) POSTs booking id, dates, and the lock's device id (`[PROPERTYTEMPLATE8]`) to a **Make scenario** (`5738113`, hook `hook.eu1.make.com/xohk7…`).
2. Make generates the igloohome PIN and writes it back to the booking as the `IGLOOPIN` booking-info code.
3. Beds24 auto action **586256 "Send igloohome PIN to guest"** (on check-in) sends it via `[BOOKINGINFOCODETEXT:IGLOOPIN]`, plus per-property lock instructions held in Room Templates (FR=`[ROOMTEMPLATE1]`, EN=`[ROOMTEMPLATE2]`).
4. **Velours T2 & Studio Écrin** are excluded from 586256 — their codes go via igloohome iglooConnect↔Airbnb directly.

Two lock types, two instruction blocks: igloohome **Keybox 3** (Terracotta, La Palma, Velours T2, Studio Écrin) and igloohome **Retrofit Lock** (Le Matisse, Le Fernand).

(The RemoteLock "Door Code Management" design in ARCHITECTURE.md is superseded by the above.)
