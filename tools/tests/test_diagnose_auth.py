"""Check diagnostic privacy, request limits and stop conditions without networking."""

from io import BytesIO
import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError
from urllib.request import HTTPSHandler, Request, build_opener
from urllib.response import addinfourl

import pytest

from tools import diagnose_auth as diagnostic

EMAIL = "private-email@example.com"
PASSWORD = "private-password"
SESSION = "private-session"
LOGIN = diagnostic.Response(200, {"ErrorCode": 0, "SessionId": SESSION, "Email": EMAIL})
DEVICES = diagnostic.Response(
    200,
    {
        "Groups": [
            {
                "Thermostats": [
                    {"SerialNumber": "private-serial", "Room": "private-room"}
                ]
            }
        ]
    },
)
REJECTED = diagnostic.Response(401, failure="non_json_response")


def test_baseline_success_does_not_try_other_logins() -> None:
    """A successful read stops the probe and the report contains no private data."""
    with (
        patch.object(diagnostic, "make_opener"),
        patch.object(diagnostic, "request", side_effect=[LOGIN, DEVICES]) as request,
    ):
        report = diagnostic.diagnose(EMAIL, PASSWORD, compare_login=True)
    assert report["result"] == "read_succeeded"
    assert report["attempts"][0]["reads"][0]["thermostat_count"] == 1
    assert request.call_count == 2
    exported = json.dumps(report)
    for private in (EMAIL, PASSWORD, SESSION, "private-serial", "private-room"):
        assert private not in exported
    assert SESSION not in repr(LOGIN)


def test_comparison_is_bounded_and_uses_separate_sessions() -> None:
    """Repeated rejections produce at most four logins and eight reads."""
    with (
        patch.object(diagnostic, "make_opener") as make_opener,
        patch.object(
            diagnostic, "request", side_effect=[LOGIN, REJECTED, REJECTED] * 4
        ) as request,
    ):
        report = diagnostic.diagnose(EMAIL, PASSWORD, compare_login=True)
    assert report["result"] == "no_working_read_in_tested_profiles"
    assert make_opener.call_count == 4
    assert request.call_count == 12
    assert [call.kwargs["payload"] for call in request.call_args_list[::3]] == [
        {"Email": EMAIL, "Password": PASSWORD, "Application": 7},
        {"Email": EMAIL, "Password": PASSWORD, "Application": 8},
        {"Email": EMAIL, "Password": PASSWORD},
        {"Email": EMAIL, "Password": PASSWORD, "Application": 7, "Confirm": PASSWORD},
    ]
    assert request.call_args_list[1].kwargs["params"] == {"sessionId": SESSION}
    assert request.call_args_list[2].kwargs["params"] == {"sessionid": SESSION}


def test_rejected_alternative_login_does_not_hide_later_profile() -> None:
    """An unsupported app profile is not evidence that the baseline password is bad."""
    with (
        patch.object(diagnostic, "make_opener"),
        patch.object(
            diagnostic,
            "request",
            side_effect=[LOGIN, REJECTED, REJECTED, REJECTED, LOGIN, DEVICES],
        ) as request,
    ):
        report = diagnostic.diagnose(EMAIL, PASSWORD, compare_login=True)
    assert report["result"] == "read_succeeded"
    assert report["attempts"][-1]["profile"] == "application_omitted"
    assert request.call_count == 6


def test_query_case_difference_is_reported_without_new_login() -> None:
    """A lowercase-query success is attributed to that read, using the same session."""
    with (
        patch.object(diagnostic, "make_opener"),
        patch.object(
            diagnostic, "request", side_effect=[LOGIN, REJECTED, DEVICES]
        ) as request,
    ):
        report = diagnostic.diagnose(EMAIL, PASSWORD, compare_login=True)
    assert report["result"] == "read_succeeded"
    assert report["attempts"][0]["reads"][1]["query_key"] == "sessionid"
    assert request.call_count == 3


@pytest.mark.parametrize(
    "responses,result",
    [
        ([diagnostic.Response(429)], "rate_limited_stop"),
        ([LOGIN, diagnostic.Response(429)], "rate_limited_stop"),
        ([diagnostic.Response(503)], "login_request_failed_stop"),
        (
            [diagnostic.Response(None, failure="transport_error")],
            "login_request_failed_stop",
        ),
        (
            [diagnostic.Response(200, {"ErrorCode": 2, "SessionId": ""})],
            "baseline_login_not_accepted_stop",
        ),
        (
            [LOGIN, diagnostic.Response(503)],
            "read_failed_without_http_auth_rejection_stop",
        ),
        ([LOGIN, diagnostic.Response(200, {"Groups": []})], "empty_account_stop"),
    ],
)
def test_stop_conditions(responses: list[diagnostic.Response], result: str) -> None:
    """Do not keep authenticating during service failure, throttling or bad login."""
    with (
        patch.object(diagnostic, "make_opener"),
        patch.object(diagnostic, "request", side_effect=responses) as request,
    ):
        report = diagnostic.diagnose(EMAIL, PASSWORD, compare_login=True)
    assert report["result"] == result
    assert request.call_count == len(responses)


def test_http_redirect_does_not_forward_credentials() -> None:
    """The real urllib handler chain refuses redirects before another request."""
    seen = []

    class RedirectingHTTPS(HTTPSHandler):
        def https_open(self, request: Request) -> addinfourl:
            seen.append(request.full_url)
            response = addinfourl(
                BytesIO(b""),
                {"Location": "https://different.example/collect"},
                request.full_url,
                307,
            )
            response.msg = "Temporary Redirect"
            return response

    opener = build_opener(RedirectingHTTPS(), diagnostic.NoRedirects())
    response = diagnostic.request(
        opener, "/api/authenticate/user", payload={"Email": EMAIL, "Password": PASSWORD}
    )
    assert response.status == 307
    assert seen == [diagnostic.BASE_URL + "/api/authenticate/user"]


def test_transport_error_hides_session_url() -> None:
    """urllib exceptions can include the complete session-bearing request URL."""
    opener = MagicMock()
    opener.open.side_effect = URLError(diagnostic.BASE_URL + "?sessionId=" + SESSION)
    response = diagnostic.request(
        opener, "/api/thermostats", params={"sessionId": SESSION}
    )
    assert diagnostic.summarize(response) == {
        "http_status": None,
        "response_issue": "transport_error",
    }


@pytest.mark.parametrize(
    "path,payload",
    [("/api/thermostat", {"ManualTemperature": 2500}), ("/api/thermostats", {})],
)
def test_setting_writes_are_not_allowed(path: str, payload: dict) -> None:
    """Only login POST and thermostat-list GET are available to this tool."""
    opener = MagicMock()
    with pytest.raises(ValueError, match="Unsupported diagnostic"):
        diagnostic.request(opener, path, payload=payload)
    opener.open.assert_not_called()


def test_unexpected_exception_is_not_exported(capsys: pytest.CaptureFixture) -> None:
    """The command-line boundary never prints an exception containing secrets."""
    with (
        patch("sys.argv", ["diagnose_auth.py"]),
        patch("sys.stdin.isatty", return_value=True),
        patch.object(diagnostic, "getpass", side_effect=[EMAIL, PASSWORD]),
        patch.object(diagnostic, "diagnose", side_effect=RuntimeError(SESSION)),
    ):
        assert diagnostic.main() == 1
    captured = capsys.readouterr()
    assert SESSION not in captured.err
    assert not captured.out
