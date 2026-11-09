"""Constants for the Solar Monitor integration."""

from datetime import timedelta
import logging

DOMAIN = "solar_monitor"
LOGGER = logging.getLogger(__package__)

# The monitor reads the gateway every 20 s while anything has asked within the
# last 5 minutes. Asking every 30 s keeps it there; asking faster returns the
# same reading.
SCAN_INTERVAL = timedelta(seconds=30)

# The monitor's slowest normal reading interval is 15 minutes. A reading older
# than that means it is not hearing from the gateway, and a power figure that
# old would be shown as if it were live. Energy totals stay: they just pause.
STALE_AFTER_SEC = 15 * 60

# The /api/now shape this integration is written against. The monitor bumps it
# only when a field is removed or changes meaning (API.md in the firmware repo).
API_VERSION = 1
