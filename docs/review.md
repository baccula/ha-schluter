# Baseline review and feature map

Baseline: Home Assistant Core tag **2026.11.1**, integration `schluter`, depending
on `py-schluter==0.1.7`. See the
[original integration](https://github.com/home-assistant/core/tree/2026.11.1/homeassistant/components/schluter)
and [original client](https://github.com/prairieapps/py-schluter).

| Existing behavior | Updated behavior | Regression evidence |
| --- | --- | --- |
| YAML email/password | GUI setup plus automatic YAML import | config-flow and YAML migration tests |
| All account thermostats discovered at setup | Same, plus later discovery | empty-account and subsequent discovery test |
| Serial-number unique IDs and room names | Same serial identities; device registry names | registry migration test |
| Current and target temperatures | Same half-degree Celsius rounding; HA handles Fahrenheit | client parsing and Fahrenheit tests |
| Heating or idle; heat-only HVAC mode | Preserved | climate state and mode test |
| Device-specific minimum/maximum | Preserved | climate limit test |
| Target writes enter permanent/manual mode and clear vacation | Preserved exactly | outgoing HTTP payload test |
| No return-to-schedule command, off mode, or energy entities | No invented features | README documents scope |

Confirmed defects and risks in the baseline:

- One session is captured at startup and retained by the coordinator and every
  entity. There is no refresh after authentication expiry or rejection.
- The client's cache stores a session as a tuple because of a trailing comma;
  deserialization wraps it again. The replacement uses a validated string in memory.
- A failed first coordinator refresh can leave `coordinator.data` unset before
  `.items()` is accessed. Startup now uses HA's retryable first-refresh lifecycle.
- The API's `Online` flag is ignored. Missing devices cause direct dictionary
  lookups to fail. Availability now includes account, presence, and online state.
- The boolean returned by `set_temperature` is ignored; command rejection can
  look successful. Command outcomes are now checked and translated to action errors.
- There is no GUI credential recovery, config-entry unload, device registry
  metadata, or test suite for this integration at the baseline tag.
- The client logs authentication payloads and raw response bodies at debug level.
  The new library emits no payload logging and sanitizes transport exceptions.

The user's restart-dependent unavailability is consistent with the session
lifetime problem, but is not yet proven to have that cause on their device.
Acceptance testing must cover the real service; the automated responses are
synthetic, derived from the existing API contract, not captured from the home.

The Core fork existed before this work. It was reused without replacing its
default branch. GitHub denied a redundant fork-creation call (HTTP 403); the
existing fork remains the source lineage for this work.
