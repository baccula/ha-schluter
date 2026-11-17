# Hardware acceptance: release gate

Target: Home Assistant **2026.11.1**, USA, Schluter DITRA Wi-Fi.
The identifier supplied in chat is intentionally not embedded in public fixtures.
Run these tests after backing up. Record date, release, thermostat firmware,
entity ID, and pass/fail observations. No passwords or raw tokens are needed.

1. **Migration:** install the candidate with the existing YAML still present.
   Confirm one account entry, the original entity IDs, custom names, and working
   dashboards. Remove YAML only after success. Run one existing automation.
2. **Read parity:** compare current/target temperature and heating/idle with the
   thermostat and Schluter app. Check Fahrenheit values and min/max limits.
3. **Control:** note the old mode and target. Set a modest, safe target you select.
   Confirm physical and app changes and permanent/manual mode. Restore the old
   target and use the thermostat's Return to Schedule when appropriate.
4. **Primary recovery test:** briefly block the HA host's access to the Schluter
   service, leaving thermostat power on. Confirm `unavailable`. Restore access;
   confirm automatic recovery within two normal polling intervals without
   reloading the integration or restarting HA. Repeat this cycle three times.
5. **Device Wi-Fi:** temporarily disconnect the thermostat from Wi-Fi using your
   normal network controls. Reconnect it and confirm HA recovers once the service
   reports it online. Do not power-cycle the heating circuit for this test.
6. **Startup outage:** start HA with its Schluter connection unavailable, then
   restore connectivity. The entry should retry and recover automatically.
7. **Session endurance:** leave the candidate running for at least 48 hours,
   including overnight. Confirm session renewal and no restart-dependent
   unavailability. Record any server rate-limit messages.
8. **Reauthentication:** if practical, change the account password through Schluter
   and invalidate existing sessions. HA should eventually offer reauthentication;
   the new password should recover the same entry and entities. Password changes
   do not necessarily revoke active vendor sessions immediately.
9. **Unload/reload:** use the integration menu to reload it; confirm no duplicate
   entities. Do not delete the entry to test reload.
10. **Rollback:** verify that the backup and original YAML are available and that
    the documented removal path is clear. Restore the backup if migration changes
    entity references unexpectedly.

Release readiness requires successful real-device results, passing automated
checks, review of the implementation, and a published installable artifact.
An automated test pass does not establish compatibility with all vendor response
variants or confer an official Silver tier.

## First installation result

Release **0.1.0rc1**, Home Assistant **2026.11.1**, USA, DITRA Wi-Fi.
Reported by the home tester on 2026-11-11:

- Backup verified and package checks passed.
- Home Assistant restarted once; all 92 previously loaded integrations recovered.
- The Schluter account imported.
- Thermostat reads returned HTTP 401 immediately after successful login.
- The legacy HTTP client reproduced the same failure.
- The official mobile app works normally with the account.
- Signing in at the official E Wi-Fi website produces: "An error occurred while
  processing your request."

**Initial result (subsequently recovered):** Import alone was a partial migration result: entity
continuity, read/control parity, and recovery/endurance have not been verified
on the thermostat. No replacement release is claimed to fix this failure.

Additional automated tests reproduce fresh-session rejection at startup and
during polling. They confirm that setup retries continue across repeated
failures, polling resumes after successful reads, and no reauthentication flow
starts merely because a newly issued session is rejected. These tests use
synthetic HTTP responses and do not establish the cause of the home failure.

The app/website difference makes comparing authentication paths the next useful
step. The website error and API 401s do not establish a shared root cause. Recent
third-party clients still use the same API host and application code 7; there is
not yet evidence that a general migration to a different API is required.

Use the [read-only authentication diagnostic](authentication-diagnostic.md) to
compare request variants without installing another integration or changing
thermostat settings. Another HA restart is not a useful first diagnostic step
for an immediately rejected fresh session.

## Home acceptance update

The maintainer reported on **2026-11-12** that the native app, website and rc1
were working again. They explicitly confirmed that the integration recovered
without restarting Home Assistant or reloading the integration. On
**2026-11-17**, they reported rock-solid operation and confirmed the requested
functional checks, including temperature changes and existing automations.
This exceeds the planned 48-hour endurance period.

These are user-reported live-device results on rc1. They strongly support a
vendor service outage as the cause of the initial failure; no vendor incident
confirmation or independent account logs were obtained. No authentication
workaround was applied. The speculative authentication diagnostic was not needed.

Passed home release checks: working readings/control, preserved entity and
automation use, recovery after the cloud outage without restart/reload, and
sustained operation beyond 48 hours. Separate controlled device-Wi-Fi outages,
password-change reauthentication, and a performed rollback were not reported;
these should not be represented as completed hardware tests.

The next candidate, rc2, changes the reauthentication input type annotation to
match Home Assistant and strengthens flow recovery tests. Authentication,
polling and thermostat commands retain the implementation tested at home.
