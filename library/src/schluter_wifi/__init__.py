"""Asynchronous client for Schluter DITRA-HEAT E Wi-Fi thermostats."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import math
from time import monotonic
from typing import Any

import aiohttp

BASE_URL = "https://ditra-heat-e-wifi.schluter.com"
SESSION_LIFETIME = 55 * 60


class SchluterError(Exception):
    """A sanitized error that never includes credentials or response bodies."""


class AuthenticationError(SchluterError):
    """The service rejected the account credentials."""


class CommunicationError(SchluterError):
    """Communication failed; a later request may succeed."""


class RateLimitError(CommunicationError):
    """The service asked the caller to wait."""

    def __init__(self, retry_after: float) -> None:
        super().__init__("Schluter rate limit reached")
        self.retry_after = retry_after


class CommandError(SchluterError):
    """The service did not accept a command."""


class _SessionRejected(CommunicationError):
    """The current session is no longer accepted."""


def _temperature(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("Invalid temperature")
    if not math.isfinite(value):
        raise ValueError("Invalid temperature")
    # Preserve the half-degree Celsius precision of py-schluter 0.1.7.
    return round(value / 100 * 2) / 2


@dataclass(frozen=True, slots=True)
class Thermostat:
    """A snapshot of the thermostat's reported state, in Celsius."""

    serial_number: str
    name: str
    temperature: float
    target_temperature: float
    min_temperature: float
    max_temperature: float
    online: bool
    heating: bool
    software_version: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Thermostat:
        """Validate the fields needed to report and control a thermostat."""
        serial = data["SerialNumber"]
        if (
            not isinstance(serial, (str, int))
            or isinstance(serial, bool)
            or not str(serial)
        ):
            raise ValueError("Invalid serial number")
        if not isinstance(data["Room"], str):
            raise ValueError("Invalid room name")
        if type(data["Online"]) is not bool or type(data["Heating"]) is not bool:
            raise ValueError("Invalid thermostat status")
        minimum = _temperature(data["MinTemp"])
        maximum = _temperature(data["MaxTemp"])
        if minimum > maximum:
            raise ValueError("Invalid thermostat limits")
        return cls(
            serial_number=str(serial),
            name=data["Room"],
            temperature=_temperature(data["Temperature"]),
            target_temperature=_temperature(data["SetPointTemp"]),
            min_temperature=minimum,
            max_temperature=maximum,
            online=data["Online"],
            heating=data["Heating"],
            software_version=str(data["SWVersion"]) if data.get("SWVersion") else None,
        )


class SchluterClient:
    """Serialize account requests and renew sessions without restarting callers.

    The caller owns the aiohttp session. This client does not persist credentials,
    log HTTP payloads, or retry commands after an ambiguous transport failure.
    """

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._session_id: str | None = None
        self._expires_at = 0.0
        self._retry_at = 0.0
        self._lock = asyncio.Lock()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if (delay := self._retry_at - monotonic()) > 0:
            raise RateLimitError(delay)
        try:
            async with self._session.request(
                method,
                BASE_URL + path,
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=False,
                **kwargs,
            ) as response:
                if response.status == 429:
                    delay = self._retry_delay(response.headers.get("Retry-After"))
                    self._retry_at = monotonic() + delay
                    raise RateLimitError(delay)
                if response.status in (401, 403):
                    raise _SessionRejected("Schluter session was rejected")
                if response.status != 200:
                    raise CommunicationError(
                        f"Schluter returned HTTP {response.status}"
                    )
                data = await response.json()
        except aiohttp.ClientError, TimeoutError, ValueError:
            # aiohttp exceptions can contain a URL with the session ID.
            raise CommunicationError(
                "Unable to read a valid Schluter response"
            ) from None
        if not isinstance(data, dict):
            raise CommunicationError("Unexpected Schluter response format")
        return data

    @staticmethod
    def _retry_delay(value: str | None) -> float:
        if value is not None:
            try:
                delay = float(value)
            except ValueError:
                try:
                    delay = (
                        parsedate_to_datetime(value) - datetime.now(UTC)
                    ).total_seconds()
                except ValueError, TypeError, OverflowError:
                    return 60
            if math.isfinite(delay):
                return max(1, delay)
        return 60

    async def _authenticate(self) -> None:
        self._session_id = None
        try:
            data = await self._request(
                "POST",
                "/api/authenticate/user",
                json={
                    "Email": self._username,
                    "Password": self._password,
                    "Application": 7,
                },
            )
        except _SessionRejected:
            raise AuthenticationError(
                "Schluter rejected the account credentials"
            ) from None
        if data.get("ErrorCode") in (1, 2):
            raise AuthenticationError("Schluter rejected the account credentials")
        if (
            data.get("ErrorCode") != 0
            or not isinstance(data.get("SessionId"), str)
            or not data["SessionId"]
        ):
            raise CommunicationError("Schluter did not return a valid login session")
        self._session_id = data["SessionId"]
        self._expires_at = monotonic() + SESSION_LIFETIME

    async def _authenticated_request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        if self._session_id is None or monotonic() >= self._expires_at:
            await self._authenticate()
        params = kwargs.pop("params", {})
        for attempt in range(2):
            try:
                data = await self._request(
                    method,
                    path,
                    params={**params, "sessionId": self._session_id},
                    **kwargs,
                )
                # Some service versions report rejected sessions in a 200 response.
                if method == "GET" and data.get("ErrorCode", 0) != 0:
                    raise _SessionRejected("Schluter rejected the request")
                return data
            except _SessionRejected:
                self._session_id = None
                if attempt:
                    raise CommunicationError(
                        "Schluter rejected the renewed session"
                    ) from None
                await self._authenticate()
            except CommunicationError:
                self._session_id = None
                raise
        raise AssertionError("Unreachable")

    async def async_get_thermostats(self) -> dict[str, Thermostat]:
        """Read all thermostats. Missing devices are absent from the result."""
        async with self._lock:
            data = await self._authenticated_request("GET", "/api/thermostats")
            try:
                result = {}
                for group in data["Groups"]:
                    for item in group["Thermostats"]:
                        thermostat = Thermostat.from_json(item)
                        if thermostat.serial_number in result:
                            raise ValueError("Duplicate thermostat")
                        result[thermostat.serial_number] = thermostat
            except KeyError, TypeError, ValueError:
                self._session_id = None
                raise CommunicationError("Invalid Schluter thermostat data") from None
            return result

    async def async_set_temperature(
        self, serial_number: str, temperature: float
    ) -> None:
        """Set a permanent target; do not replay commands after a timeout."""
        if not math.isfinite(temperature):
            raise ValueError("Temperature must be finite")
        async with self._lock:
            data = await self._authenticated_request(
                "POST",
                "/api/thermostat",
                params={"serialnumber": serial_number},
                json={
                    "ManualTemperature": round(temperature * 100),
                    "RegulationMode": 3,
                    "VacationEnabled": False,
                },
            )
            if data.get("Success") is not True:
                raise CommandError("Schluter did not accept the temperature change")
