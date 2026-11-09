# Solar Monitor for Home Assistant

Brings your [Solar Monitor](https://www.solar-monitor.app) into Home Assistant:
live solar, grid and home power, lifetime energy for the Energy dashboard, and
every panel as its own device.

It works with every SunPower PVS gateway the Solar Monitor supports, old
firmware or new. The monitor deals with the gateway, so there is no sign-in to
set up, no second network port, and no Raspberry Pi bridge.

## Requirements

- Solar Monitor firmware **1.7.0** or later
- Home Assistant **2026.11** or later

## Install

1. In Home Assistant, open **Marketplace**, then **⋮ → Custom repositories**.
2. Add `https://github.com/solarmonitorapp/ha-solar-monitor` as an **Integration**.
   The first time you add a custom repository, Home Assistant asks you to
   connect GitHub.
3. Open **Solar Monitor** in the Marketplace and download it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → Solar Monitor**,
   and enter your monitor's IP address. You'll find it in the monitor's
   dashboard under **Debug → Monitor**, or in your router.

Home Assistant may also find the monitor by itself and offer to set it up.

## What you get

**Solar Monitor device**

| Entity | |
|---|---|
| Solar production | kW, right now |
| Grid power | kW. Positive while buying, negative while selling |
| Home load | kW. Production plus grid |
| Exporting | On while selling to the grid |
| Solar produced, Grid bought, Grid sold | kWh, lifetime totals |
| Solar produced today | kWh since midnight |
| Panels reporting | How many panels the gateway is hearing from |
| Reading age, Gateway firmware | Diagnostics |

**One device per panel**: power, lifetime energy, inverter temperature, and
**Reporting**, which is the health signal. DC voltage and current are there
too, disabled by default.

### Energy dashboard

Under **Settings → Dashboards → Energy**, choose:

- Solar production: **Solar produced**
- Grid consumption: **Grid bought**
- Return to grid: **Grid sold**

## Good to know

- **Unknown means unknown.** A system without a grid meter has no grid,
  load or bought/sold figures, and those entities show *unknown* rather than 0.
  Some gateways can't split the grid into bought and sold; then those two are
  unknown, while grid power still works.
- **The readings update every 30 seconds.** The monitor reads the gateway every
  20 seconds while anything is asking, so polling faster gains nothing.
- **If the monitor stops hearing from the gateway**, the right-now power
  readings become unavailable after 15 minutes, instead of showing an old figure
  as current. The energy totals stay; they just pause.
- **"Inverter temperature" is the micro-inverter's heatsink**, not the
  panel's surface.

## For developers

The integration reads one document, the monitor's `/api/now`, and nothing
else. The same API is open to anything on your network; see the
[API documentation](https://www.solar-monitor.app).

## License

Apache License 2.0. The Solar Monitor name and logo are trademarks of Solar
Monitor LLC and are not covered by the license.
