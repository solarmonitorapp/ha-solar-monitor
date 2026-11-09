"""Client for a Solar Monitor's /api/now.

The integration reads this one document and nothing else. Every difference
between gateway generations is ironed out by the monitor's firmware, so nothing
here knows about PVS firmware, sign-in or meter types.
"""

import asyncio
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .const import API_VERSION


class SolarMonitorError(Exception):
    """The monitor could not be read."""


class SolarMonitorConnectionError(SolarMonitorError):
    """The monitor did not answer, or answered with something unreadable."""


class SolarMonitorUnsupportedError(SolarMonitorError):
    """The monitor answered, but not with an /api/now this integration knows.

    Firmware before 1.7.0 sends no apiVersion.
    """


def normalize_host(host: str) -> str:
    """Accept what people paste: '192.168.1.40', 'http://solar-monitor.local/'."""
    host = host.strip()
    if "://" in host:
        host = urlsplit(host).netloc
    return host.split("/", 1)[0].rstrip(".")


class SolarMonitorClient:
    """Reads /api/now from one monitor."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self.host = host
        self._session = session

    async def now(self) -> dict[str, Any]:
        """Return the monitor's /api/now document."""
        try:
            # /api/now is answered from the monitor's last reading, so it is
            # quick unless the monitor is unreachable.
            async with asyncio.timeout(10):
                response = await self._session.get(f"http://{self.host}/api/now")
                response.raise_for_status()
                data = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as error:
            raise SolarMonitorConnectionError(str(error)) from error
        if not isinstance(data, dict) or data.get("apiVersion") != API_VERSION:
            raise SolarMonitorUnsupportedError(
                f"apiVersion {data.get('apiVersion') if isinstance(data, dict) else None}"
            )
        return data
