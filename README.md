# Schluter DITRA-HEAT Wi-Fi for Home Assistant

GUI configuration and automatic communication recovery for the existing
Schluter DITRA-HEAT E Wi-Fi integration. Minimum Home Assistant: **2026.11.1**.
Maintainer: [@baccula](https://github.com/baccula).

**Release candidate. Home testing has confirmed automatic outage recovery,
stable operation beyond 48 hours, temperature control, and existing automations.**
See the [acceptance record](docs/acceptance.md#home-acceptance-update).
Automated tests also use synthetic responses. This is not an officially awarded
Home Assistant quality tier; the implementation is evaluated against the Bronze
and Silver rules. Remaining Core submission checks and standalone library publication are pending.
See [review and feature parity](docs/review.md), [quality evidence](docs/quality.md),
and [acceptance testing](docs/acceptance.md).

## Supported functions

All thermostats registered to your Schluter account appear as climate entities.
They report current temperature, target temperature, heating/idle state, and the
thermostat's minimum and maximum temperatures. You can set the target temperature.
Home Assistant converts temperatures for Celsius and Fahrenheit display.

Setting a target uses the same permanent/manual mode as the built-in integration:
it overrides the thermostat's schedule and disables vacation mode. To resume the
schedule, use **Return to Schedule** on the thermostat. There is no off mode,
schedule editor, energy sensor, or separate floor/air sensor in this release.
Compatibility with DITRA-HEAT RS1/Schluter Smart or other API families is not claimed.

## Install through Marketplace

This package deliberately retains the `schluter` domain to preserve existing
entities. It replaces the built-in integration and therefore uses a **custom
repository link**, not the public Marketplace catalog.

Install the published `v0.1.0rc2` prerelease:

1. Create a Home Assistant backup, including configuration and entity registries.
2. Add this repository in **Settings > Marketplace** as a custom integration
   repository, then open its Marketplace page.
3. Open the three-dot menu, choose **Install another version**, and select
   **`v0.1.0rc2`**. Acknowledge that it replaces a built-in integration.
4. Restart Home Assistant so it loads the replacement.
5. Follow the migration or fresh-setup instructions below.

[Open the repository in Marketplace](https://my.home-assistant.io/redirect/marketplace_repository/?owner=baccula&repository=ha-schluter&category=integration)

**Include pre-releases** in the same menu makes Marketplace offer the prerelease
by default. If a previous attempt tried to download `releases/download/main/schluter.zip`,
choose **Refresh information** before retrying. When Marketplace selects `main`,
it now installs the integration from the repository files. Choose `v0.1.0rc2`
to install the published package and record that version in Marketplace.

For manual installation, extract the contents of `schluter.zip` into
`<config>/custom_components/schluter/`, then restart. `manifest.json` must be
directly inside that directory, not inside another `schluter/` subdirectory.

## Migrate an existing installation

Keep your existing `schluter:` YAML configuration for the first restart. The
integration imports it into a GUI-managed config entry, reusing thermostat
serial numbers so entity IDs, custom names, history, dashboards, and automations
can keep their existing references. A temporary outage does not prevent import:
Home Assistant retries the new entry when connectivity returns.

After the entry and your existing climate entities are working, remove the
`schluter:` block from `configuration.yaml`. Repeated imports do not overwrite a
password subsequently changed through the UI. The old `.schluter.conf` session
cache is unused; you may remove it after validating the migration.

Do not delete the existing entities as part of migration. Verify their entity
IDs and one existing automation using the acceptance checklist before discarding
your backup.

## Fresh setup and account parameters

Register the thermostat with the Schluter DITRA-HEAT E Wi-Fi service first.
Then use **Settings > Devices & services > Add integration > Schluter**.

| Field | Purpose |
| --- | --- |
| Email | Email for the Schluter DITRA-HEAT account. Surrounding whitespace is removed and the account identity is case-insensitive. |
| Password | Current Schluter password. Stored in Home Assistant's config entry, not YAML or the old session cache. |

No options are required. Account polling is fixed at 60 seconds to avoid
excessive cloud requests. All devices on the account are discovered; there is no
serial-number input. The device identifier displayed by the thermostat is not
used as a substitute for the API serial number.

If Schluter rejects the credentials, Home Assistant offers **Reauthenticate**.
Enter the current password there. A successful reauthentication reloads the same
entry and retains its entity identities.

## Communication and recovery

Network errors and temporary server failures make entities unavailable while
scheduled polling continues. The last snapshot is retained internally; stale
temperatures are not presented as a healthy connection. Offline or temporarily
missing thermostats become available again when the API reports them online.

Sessions are renewed proactively and after explicit rejection. Rejection of a
newly issued session remains a retryable communication problem, rather than
permanently stopping polling. Only rejection of the account login triggers UI
reauthentication. The server's `Retry-After` response is honored, so recovery may
take longer during throttling.

A failed temperature command raises a visible action error. A timeout is
ambiguous: the thermostat may have accepted the change. The integration does
not blindly replay the command; check the next reported target or the thermostat
before trying again. Successful commands request a state refresh.

## Troubleshooting

- If unavailable, check the Schluter app and internet access. After service
  returns, allow at least two polling intervals; allow longer if rate limited.
- If prompted to reauthenticate, verify the account password in the Schluter app
  and update it in Home Assistant.
- If one device is unavailable, check its Wi-Fi and power; other online devices
  can remain usable.
- If a thermostat does not appear, verify that it is registered to this account
  and uses the E Wi-Fi service. Newly registered devices are added on later polls.
- For persistent failures, record the Home Assistant version, release version,
  failure time, and the sanitized error message. Do not post credentials,
  session tokens, or raw account responses.

The new client does not log credentials, session IDs, or response bodies.
It uses verified HTTPS and Home Assistant's shared HTTP session. It has no local
control fallback; thermostat scheduling continues independently of this integration.

## Remove or roll back

To remove the integration, remove its config entry in **Settings > Devices &
services**, then uninstall the custom repository through Marketplace and restart.
Remove any remaining legacy YAML block to prevent it being imported again.

To return to the old built-in integration, uninstall the custom package, restore
your original `schluter:` YAML configuration, and restart. The built-in 2026.11.1
integration does not support the new config entry; use your backup for a complete
rollback that also restores registry state. Keep the backup until acceptance
testing has finished.

## Development and upstream preparation

The canonical integration implementation is on the Core fork's
`codex/schluter-modernization` branch. `python tools/package.py <core-checkout>`
produces this custom package and `dist/schluter.zip`. The client is developed
independently in `library/`. See [Core preparation](docs/core-submission.md) for
remaining publication and review steps.
