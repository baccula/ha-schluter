# Optional authentication diagnostic

The November home outage recovered without a client authentication change.
This tool is retained for future troubleshooting and is not needed for the
currently working installation. The investigation below describes the original
failure, not an active release blocker.

The first home installation can use the official mobile app, but the official
website fails during sign-in and both rc1 and the legacy client receive HTTP
401 on thermostat reads after login. The cause is unconfirmed.

`tools/diagnose_auth.py` compares a small set of published request variants.
It performs login POSTs and thermostat-list GETs only. It does not write heating
settings, edit Home Assistant configuration, install packages, or require an HA
restart. Creating fresh API sessions may affect other clients if the vendor
invalidates earlier sessions; the integration is designed to renew rejected ones.

## Run once

Download `tools/diagnose_auth.py`. In an interactive terminal, preferably in the
same network environment where the legacy client reproduced the failure, run:

```sh
python3 diagnose_auth.py --compare-login
```

Python 3.10 or newer is sufficient; no additional packages are needed. Enter the
account email and password at the hidden local prompts. Do not put them in the
command, chat, or a script. Share only the JSON report printed at the end.

The report includes HTTP status codes, numeric error codes, whether a session ID
was returned, and thermostat counts. It excludes the email, password, session
IDs, cookies, device IDs, names, temperatures and raw responses. The script sends
credentials only to `https://ditra-heat-e-wifi.schluter.com`, verifies TLS and
refuses redirects. It retains no credential file and stops on throttling rather
than retrying. There are at most four login requests and eight read requests;
the first successful nonempty list stops the comparison.

## What is compared

Each login profile uses an isolated cookie jar and its own fresh session. Reads
compare the query keys `sessionId` and `sessionid` only after an HTTP 401/403.

| Profile | Login difference | Public evidence |
| --- | --- | --- |
| `application_7` | Same JSON fields as rc1 | [aioschluter](https://github.com/IngoS11/aioschluter/blob/master/aioschluter/__init__.py) and [Schluter Plus](https://github.com/superbam/ha-schluter-plus/blob/main/custom_components/schluter_plus/api.py) |
| `application_8_historical_mobile` | Application 8 instead of 7 | [2019 mobile-app protocol report](https://community.openhab.org/t/anyone-ever-looked-into-ditra-heat-floor-warming-wifi-thermostat/43823/6); current compatibility is unknown |
| `application_omitted` | No Application field | [Homebridge client's signIn method](https://github.com/derekprior/homebridge-schluter-thermostat/blob/main/src/schluter-api.ts) |
| `application_7_with_confirm` | Adds Confirm with the same password | [Control4 client](https://github.com/finitelabs/control4-schluter/blob/main/src/schluter/client/legacy.lua) |

These are diagnostic comparisons, not endorsed replacements for the production
login contract. All requests remain on the original Schluter host. The probe
uses Python's standard-library HTTP client, so a successful baseline alone does
not identify a particular aiohttp defect or exclude network/client differences.

## Interpreting results

- `read_succeeded`: the last attempt identifies a profile and query spelling
  that returned a nonempty thermostat list. This is evidence for a focused
  compatibility test, not proof of write parity or production readiness.
- `empty_account_stop`: the service returned a list with zero thermostats. This
  is not a usable integration result; verify account/profile association.
- `no_working_read_in_tested_profiles`: none of the tested profiles returned a
  usable list. This does not prove that the mobile app uses any of these profiles.
- `baseline_login_not_accepted_stop`: HTTP 200 alone did not establish a valid
  login. The baseline must return ErrorCode 0 and a nonempty SessionId.
- Results ending in `stop` for rate limits, transport/server errors, or unexpected
  responses are inconclusive. Do not repeatedly run the probe during throttling.

If all variants fail while the mobile app keeps working, the next evidence
needed is the app's current authentication protocol or vendor clarification.
Do not share an unredacted browser HAR, account payload, or token to obtain it.
