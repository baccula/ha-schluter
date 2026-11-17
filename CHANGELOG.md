# Changelog

## 0.1.0rc2

- Match Home Assistant's expected reauthentication input type.
- Verify successful completion of setup and reauthentication after errors.
- Verify repeated fresh-session rejection recovers at startup and during polling.
- Record successful home outage recovery, endurance, control and automation checks.
- Retain rc1 authentication, polling and thermostat command behavior.

## 0.1.0rc1

- Add GUI account setup, YAML import and reauthentication.
- Renew sessions automatically and recover from communication failures.
- Preserve existing climate entity identities and target-temperature control.
