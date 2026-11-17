"""Exercise the real aiohttp request boundary with synthetic vendor responses."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from functools import partial
import logging
import re
from unittest.mock import MagicMock, patch

import aiohttp
from aioresponses import aioresponses
import pytest

from custom_components.schluter._vendor.schluter_wifi import (
    BASE_URL,
    AuthenticationError,
    CommandError,
    CommunicationError,
    RateLimitError,
    SchluterClient,
    Thermostat,
)

AUTH = BASE_URL + "/api/authenticate/user"
READ = re.compile(re.escape(BASE_URL + "/api/thermostats") + r"\?.*")
WRITE = re.compile(re.escape(BASE_URL + "/api/thermostat") + r"\?.*")
LOGIN = {"ErrorCode": 0, "SessionId": "secret-session"}
DEVICE = {
    "SerialNumber": "TEST123",
    "Room": "Bathroom",
    "Temperature": 2250,
    "SetPointTemp": 2400,
    "MinTemp": 500,
    "MaxTemp": 4000,
    "Online": True,
    "Heating": True,
    "SWVersion": "1.0",
}
DATA = {"Groups": [{"Thermostats": [DEVICE]}]}


@pytest.fixture
def responses():
    """Mock HTTP without replacing any client methods."""
    with (
        patch(
            "aioresponses.core.ClientResponse",
            partial(aiohttp.ClientResponse, stream_writer=MagicMock()),
        ),
        aioresponses() as mock,
    ):
        yield mock


@pytest.fixture
async def client():
    """The caller owns and closes the injected session."""
    async with aiohttp.ClientSession() as session:
        yield SchluterClient(session, "test@example.com", "secret-password")


async def test_read_and_set(client, responses, caplog):
    caplog.set_level(logging.DEBUG)
    responses.post(AUTH, payload=LOGIN)
    responses.get(READ, payload=DATA, repeat=True)
    responses.post(WRITE, payload={"Success": True})
    data = await client.async_get_thermostats()
    assert data["TEST123"] == Thermostat(
        "TEST123", "Bathroom", 22.5, 24, 5, 40, True, True, "1.0"
    )
    await client.async_set_temperature("TEST123", 25.5)
    await client.async_get_thermostats()
    calls = [call for calls in responses.requests.values() for call in calls]
    assert len(calls) == 4
    assert calls[0].kwargs["json"] == {
        "Email": "test@example.com",
        "Password": "secret-password",
        "Application": 7,
    }
    assert calls[-1].kwargs["json"] == {
        "ManualTemperature": 2550,
        "RegulationMode": 3,
        "VacationEnabled": False,
    }
    assert "secret-password" not in caplog.text
    assert "secret-session" not in caplog.text
    assert all(call.kwargs["allow_redirects"] is False for call in calls)


@pytest.mark.parametrize(
    "status,payload", [(401, None), (403, None), (200, {"ErrorCode": 3})]
)
async def test_expired_session_recovers(client, responses, status, payload):
    responses.post(AUTH, payload=LOGIN, repeat=True)
    responses.get(READ, payload=DATA)
    responses.get(READ, status=status, payload=payload)
    responses.get(READ, payload=DATA)
    await client.async_get_thermostats()
    assert (await client.async_get_thermostats())["TEST123"].online
    auth_calls = sum(
        len(calls)
        for (method, url), calls in responses.requests.items()
        if str(url) == AUTH
    )
    assert auth_calls == 2


async def test_session_age_refresh(client, responses):
    responses.post(AUTH, payload=LOGIN, repeat=True)
    responses.get(READ, payload=DATA, repeat=True)
    with patch(
        "custom_components.schluter._vendor.schluter_wifi.monotonic", return_value=0
    ) as clock:
        await client.async_get_thermostats()
        clock.return_value = 3600
        await client.async_get_thermostats()
    auth_calls = sum(
        len(calls)
        for (method, url), calls in responses.requests.items()
        if str(url) == AUTH
    )
    assert auth_calls == 2


async def test_repeated_session_rejection_is_retryable(client, responses):
    responses.post(AUTH, payload=LOGIN, repeat=True)
    responses.get(READ, status=401)
    responses.get(READ, status=401)
    responses.get(READ, payload=DATA)
    with pytest.raises(CommunicationError, match="renewed session"):
        await client.async_get_thermostats()
    assert (await client.async_get_thermostats())["TEST123"].online


@pytest.mark.parametrize(
    "error", [TimeoutError(), aiohttp.ClientConnectionError("secret-session")]
)
async def test_connection_failure_recovers(client, responses, error):
    responses.post(AUTH, payload=LOGIN, repeat=True)
    responses.get(READ, exception=error)
    responses.get(READ, payload=DATA)
    with pytest.raises(CommunicationError) as caught:
        await client.async_get_thermostats()
    assert "secret-session" not in str(caught.value)
    assert caught.value.__suppress_context__
    assert (await client.async_get_thermostats())["TEST123"].online


@pytest.mark.parametrize("status", [302, 500, 502, 503])
async def test_server_failure_recovers(client, responses, status):
    responses.post(AUTH, payload=LOGIN, repeat=True)
    responses.get(READ, status=status)
    responses.get(READ, payload=DATA)
    with pytest.raises(CommunicationError, match="HTTP"):
        await client.async_get_thermostats()
    assert (await client.async_get_thermostats())["TEST123"].online


@pytest.mark.parametrize(
    "status,payload",
    [
        (401, {}),
        (403, {}),
        (200, {"ErrorCode": 1}),
        (200, {"ErrorCode": 2}),
    ],
)
async def test_bad_credentials(client, responses, status, payload):
    responses.post(AUTH, status=status, payload=payload)
    with pytest.raises(AuthenticationError):
        await client.async_get_thermostats()


@pytest.mark.parametrize(
    "payload",
    [
        {"ErrorCode": 99},
        {"ErrorCode": 0},
        {"ErrorCode": 0, "SessionId": ""},
        {"ErrorCode": 0, "SessionId": 123},
        [],
    ],
)
async def test_invalid_login_response_is_not_bad_password(client, responses, payload):
    responses.post(AUTH, payload=payload)
    with pytest.raises(CommunicationError):
        await client.async_get_thermostats()


@pytest.mark.parametrize(
    "payload", [{}, {"Groups": None}, {"Groups": [{"Thermostats": [DEVICE, DEVICE]}]}]
)
async def test_invalid_read_response(client, responses, payload):
    responses.post(AUTH, payload=LOGIN)
    responses.get(READ, payload=payload)
    with pytest.raises(CommunicationError):
        await client.async_get_thermostats()


async def test_invalid_json(client, responses):
    responses.post(AUTH, body="<html>temporarily unavailable</html>")
    with pytest.raises(CommunicationError):
        await client.async_get_thermostats()


async def test_empty_account(client, responses):
    responses.post(AUTH, payload=LOGIN)
    responses.get(READ, payload={"Groups": []})
    assert await client.async_get_thermostats() == {}


@pytest.mark.parametrize(
    "payload", [{"Success": False}, {}, {"ErrorCode": 10, "Success": False}]
)
async def test_command_rejected(client, responses, payload):
    responses.post(AUTH, payload=LOGIN)
    responses.post(WRITE, payload=payload)
    with pytest.raises(CommandError):
        await client.async_set_temperature("TEST123", 25)
    assert sum(len(calls) for calls in responses.requests.values()) == 2


async def test_ambiguous_command_not_replayed(client, responses):
    responses.post(AUTH, payload=LOGIN, repeat=True)
    responses.post(WRITE, exception=TimeoutError())
    responses.get(READ, payload=DATA)
    with pytest.raises(CommunicationError):
        await client.async_set_temperature("TEST123", 25)
    assert (await client.async_get_thermostats())["TEST123"].online
    commands = sum(
        len(calls)
        for (method, url), calls in responses.requests.items()
        if url.path == "/api/thermostat"
    )
    assert commands == 1


async def test_command_session_renewal(client, responses):
    responses.post(AUTH, payload=LOGIN, repeat=True)
    responses.post(WRITE, status=401)
    responses.post(WRITE, payload={"Success": True})
    await client.async_set_temperature("TEST123", 25)


async def test_rate_limit(client, responses):
    responses.post(AUTH, payload=LOGIN, repeat=True)
    responses.get(READ, status=429, headers={"Retry-After": "120"})
    responses.get(READ, payload=DATA)
    with patch(
        "custom_components.schluter._vendor.schluter_wifi.monotonic", return_value=0
    ) as clock:
        with pytest.raises(RateLimitError) as caught:
            await client.async_get_thermostats()
        assert caught.value.retry_after == 120
        with pytest.raises(RateLimitError):
            await client.async_get_thermostats()
        assert sum(len(calls) for calls in responses.requests.values()) == 2
        clock.return_value = 121
        assert (await client.async_get_thermostats())["TEST123"].online


@pytest.mark.parametrize(
    "header,expected",
    [(None, 60), ("bad date", 60), ("nan", 60), ("-1", 1), ("12", 12)],
)
def test_rate_delay(header, expected):
    assert SchluterClient._retry_delay(header) == expected


def test_rate_delay_http_date():
    value = format_datetime(datetime.now(UTC) + timedelta(seconds=120))
    assert 118 < SchluterClient._retry_delay(value) <= 120


async def test_concurrent_reads_share_session(client, responses):
    responses.post(AUTH, payload=LOGIN)
    responses.get(READ, payload=DATA, repeat=True)
    first, second = await asyncio.gather(
        client.async_get_thermostats(), client.async_get_thermostats()
    )
    assert first == second
    assert sum(len(calls) for calls in responses.requests.values()) == 3


@pytest.mark.parametrize(
    "key,value",
    [
        ("SerialNumber", None),
        ("SerialNumber", True),
        ("SerialNumber", ""),
        ("Room", 123),
        ("Online", "true"),
        ("Heating", 1),
        ("Temperature", True),
        ("Temperature", "20"),
        ("Temperature", float("nan")),
        ("MinTemp", 5000),
    ],
)
def test_invalid_device(key, value):
    device = {**deepcopy(DEVICE), key: value}
    with pytest.raises(ValueError):
        Thermostat.from_json(device)


def test_optional_firmware_and_numeric_serial():
    device = {**DEVICE, "SerialNumber": 123, "SWVersion": None}
    assert Thermostat.from_json(device).serial_number == "123"
    assert Thermostat.from_json(device).software_version is None


async def test_invalid_setpoint(client):
    with pytest.raises(ValueError):
        await client.async_set_temperature("TEST123", float("inf"))
