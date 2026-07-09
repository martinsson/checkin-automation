# igloohome

**Role:** Smart locks on the properties; generates the time-bound PIN delivered to each guest.

**Account / access:** see [`../../secrets/access-map.md`](../../secrets/access-map.md).

## Hardware

| Lock type | Properties |
|-----------|-----------|
| **Keybox 3** | Terracotta, La Palma, Velours T2, Studio Écrin |
| **Retrofit Lock** | Le Matisse, Le Fernand |

Each property's Keybox device id is stored in Beds24 `[PROPERTYTEMPLATE8]`
(e.g. `IGK343002588`).

## PIN delivery — two paths

- **Most properties:** PIN is generated via [Make](../make/) and delivered through
  [Beds24](../beds24/) auto action 586256. See **[Door codes](../door-codes.md)**.
- **Velours T2 & Studio Écrin:** PIN delivered directly via **iglooConnect↔Airbnb**, bypassing
  Beds24.

## See also

- **[Door codes](../door-codes.md)** — full generation/delivery flow.
