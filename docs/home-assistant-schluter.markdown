---
description: Connect and control Schluter DITRA-HEAT E Wi-Fi floor heating thermostats.
ha_release: 0.108
ha_domain: schluter
---

The **Schluter** integration connects the thermostats registered to your
Schluter DITRA-HEAT E Wi-Fi account. It uses the Schluter cloud service.

## Prerequisites

Create a Schluter DITRA-HEAT account, confirm the email, and register your
thermostat using the manufacturer's setup process. Verify you can access the
thermostat in the Schluter app before setting up Home Assistant.

{% include integrations/config_flow.md %}

{% configuration_basic %}
Email:
  description: The email associated with your Schluter account.
Password:
  description: Your current Schluter account password.
{% endconfiguration_basic %}

All thermostats registered to the account are added. New devices are discovered
on later updates. No polling or device-selection options are required.

## Migrating from YAML

Existing `schluter:` YAML configuration is imported automatically. Verify the
integration and entities are working, then remove the `schluter:` block from
`configuration.yaml`. Existing thermostat serial identities are retained so
entity IDs and automation references can remain unchanged. The old
`.schluter.conf` session cache is no longer used and may be removed after
successful migration.

## Supported features

- Current and target temperature.
- Setting the target temperature.
- Heating or idle state and the thermostat's temperature limits.
- Automatic recovery after temporary communication failures.

Setting a target selects permanent/manual mode and disables vacation mode,
matching the previous integration. Thermostat schedules are ignored until you
select **Return to Schedule** on the thermostat. The integration does not expose
an off mode, schedule editing, or energy sensors.

Home Assistant handles Celsius and Fahrenheit display. The thermostat and cloud
service continue managing heating independently when Home Assistant is offline.

## Data updates and unavailable devices

The integration polls once every 60 seconds. It renews expired sessions and
continues polling after temporary network or server errors. During a failure,
affected entities become unavailable. They recover automatically when
communication succeeds. Server rate limits can extend the time between polls.

Devices reported offline or missing by Schluter are unavailable until they return.
If the account password is rejected, Home Assistant requests reauthentication.
Enter the current password in the integration's reauthentication flow.

If a temperature command fails, Home Assistant reports an action error. A timed
out request may have reached the thermostat; check its target before repeating
the action. Commands are not replayed after ambiguous network failures.

## Troubleshooting

Check the Schluter app, the thermostat's Wi-Fi, and the Home Assistant host's
internet access. After restoring service, allow at least two polling intervals
for recovery, or longer if the cloud service is rate limiting. A restart should
not be necessary for a temporary outage. Report persistent failures with the
integration version and sanitized error text; do not include passwords or tokens.

## Removing the integration

Remove the Schluter entry from **Settings > Devices & services**. Also remove
any remaining `schluter:` YAML block so it is not imported on the next restart.
Removal from Home Assistant does not unregister the thermostat from Schluter.
