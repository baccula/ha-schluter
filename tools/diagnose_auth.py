#!/usr/bin/env python3
"""Compare Schluter login/read requests without changing thermostat settings.

Requires Python 3.10+ and only its standard library. Credentials are entered
interactively and sent only to the fixed Schluter HTTPS host. The JSON report
contains an allowlist of status codes, booleans and counts, never raw responses.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from getpass import GetPassWarning, getpass
from http.client import HTTPException
from http.cookiejar import CookieJar
import json
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    HTTPSHandler,
    OpenerDirector,
    Request,
    build_opener,
)
import warnings

BASE_URL = "https://ditra-heat-e-wifi.schluter.com"
MAX_RESPONSE_BYTES = 1024 * 1024


class NoRedirects(HTTPRedirectHandler):
    """Never forward credentials or session-bearing URLs to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class Response:
    """Hold private response data separately from the report."""

    status: int | None
    data: dict | None = field(default=None, repr=False)
    failure: str | None = None


def make_opener() -> OpenerDirector:
    """Use verified TLS, inherited proxy settings and an isolated cookie jar."""
    return build_opener(
        HTTPSHandler(context=ssl.create_default_context()),
        HTTPCookieProcessor(CookieJar()),
        NoRedirects(),
    )


def request(
    opener: OpenerDirector,
    path: str,
    *,
    payload: dict | None = None,
    params: dict | None = None,
) -> Response:
    """Read a bounded response, suppressing exceptions that may contain secrets."""
    if path not in ("/api/authenticate/user", "/api/thermostats"):
        raise ValueError("Unsupported diagnostic endpoint")
    if (path == "/api/authenticate/user") != (payload is not None):
        raise ValueError("Unsupported diagnostic method")
    url = BASE_URL + path
    if params:
        url += "?" + urlencode(params)
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers)
    try:
        try:
            response = opener.open(req, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            status = response.status
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (URLError, OSError, HTTPException, ValueError):
        return Response(None, failure="transport_error")
    if len(raw) > MAX_RESPONSE_BYTES:
        return Response(status, failure="response_too_large")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        return Response(status, failure="non_json_response")
    if not isinstance(data, dict):
        return Response(status, failure="non_object_response")
    return Response(status, data=data)


def summarize(response: Response) -> dict:
    """Export only explicitly allowed, nonidentifying response facts."""
    result = {"http_status": response.status}
    if response.failure:
        result["response_issue"] = response.failure
    data = response.data or {}
    error_code = data.get("ErrorCode")
    if type(error_code) is int and -1000 <= error_code <= 1000:
        result["error_code"] = error_code
    return result


def thermostat_count(data: dict | None) -> int | None:
    """Validate list structure without exporting names, identifiers or readings."""
    if data is None or not isinstance(data.get("Groups"), list):
        return None
    count = 0
    for group in data["Groups"]:
        if not isinstance(group, dict) or not isinstance(
            group.get("Thermostats"), list
        ):
            return None
        if not all(isinstance(device, dict) for device in group["Thermostats"]):
            return None
        count += len(group["Thermostats"])
    return count


def diagnose(email: str, password: str, *, compare_login: bool = False) -> dict:
    """Run a bounded comparison, stopping on success, throttling or service errors."""
    profiles = [("application_7", {"Application": 7})]
    if compare_login:
        profiles.extend(
            [
                ("application_8_historical_mobile", {"Application": 8}),
                ("application_omitted", {}),
                ("application_7_with_confirm", {"Application": 7, "Confirm": password}),
            ]
        )
    report = {
        "diagnostic_version": 1,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "host": "ditra-heat-e-wifi.schluter.com",
        "http_client": "python_stdlib_urllib",
        "attempts": [],
    }
    for profile, extra in profiles:
        opener = make_opener()
        login = request(
            opener,
            "/api/authenticate/user",
            payload={"Email": email, "Password": password, **extra},
        )
        login_data = login.data or {}
        session_id = login_data.get("SessionId")
        session_present = isinstance(session_id, str) and bool(session_id)
        attempt = {
            "profile": profile,
            "login": {**summarize(login), "session_id_present": session_present},
            "reads": [],
        }
        report["attempts"].append(attempt)
        if login.status == 429:
            report["result"] = "rate_limited_stop"
            return report
        if profile != "application_7" and login.status in (401, 403):
            continue
        if login.status != 200 or login.failure:
            report["result"] = "login_request_failed_stop"
            return report
        if login_data.get("ErrorCode") != 0 or not session_present:
            # The initial credentials must work before testing other app profiles.
            if profile == "application_7":
                report["result"] = "baseline_login_not_accepted_stop"
                return report
            continue
        for query_key in ("sessionId", "sessionid"):
            response = request(
                opener, "/api/thermostats", params={query_key: session_id}
            )
            count = thermostat_count(response.data)
            attempt["reads"].append(
                {
                    "query_key": query_key,
                    **summarize(response),
                    "thermostat_count": count,
                }
            )
            if response.status == 429:
                report["result"] = "rate_limited_stop"
                return report
            if (
                response.status == 200
                and count is not None
                and (response.data or {}).get("ErrorCode", 0) == 0
            ):
                report["result"] = "read_succeeded" if count else "empty_account_stop"
                return report
            if response.status not in (401, 403):
                report["result"] = "read_failed_without_http_auth_rejection_stop"
                return report
    report["result"] = "no_working_read_in_tested_profiles"
    return report


def main() -> int:
    """Prompt locally and print a sanitized report suitable for sharing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compare-login",
        action="store_true",
        help="Compare up to four published login variants (at most 12 requests).",
    )
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.error(
            "Run interactively; credentials cannot be passed in arguments or stdin."
        )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            email = getpass("Schluter email (hidden): ").strip()
            password = getpass("Schluter password (hidden): ")
        if not email or not password:
            print("Email and password are required.", file=sys.stderr)
            return 2
        report = diagnose(email, password, compare_login=args.compare_login)
    except (KeyboardInterrupt, EOFError):
        print("Diagnostic cancelled.", file=sys.stderr)
        return 130
    except Exception:
        # Unexpected HTTP errors can also embed session-bearing request URLs.
        print(
            "Diagnostic could not finish; no exception details exported.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
