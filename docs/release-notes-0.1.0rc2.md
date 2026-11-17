# Schluter 0.1.0rc2

This candidate provides GUI-managed setup and automatic session recovery for
Schluter DITRA-HEAT E Wi-Fi thermostats while preserving the built-in
integration's domain, climate entity identities and temperature controls.

Home testing of rc1 confirmed recovery after a cloud outage without restarting
Home Assistant or reloading the integration, stable operation beyond 48 hours,
working temperature changes and existing automations. Rc2 preserves that runtime
behavior and corrects the reauthentication input annotation for current Home
Assistant, with stronger tests for recovering from configuration errors.

Minimum Home Assistant version: **2026.11.1**. This release replaces the built-in
`schluter` integration through a Marketplace custom repository, not the public
catalog. RS1 and European API families are not claimed to be supported.

Validation: 28 Core integration tests and 95 combined package/diagnostic tests
passed. Targeted Core and custom-package hassfest passed; the expected custom
integration domain-collision warning remains. The corrected config-flow modules
pass HA pylint. An official Silver tier is not claimed, and broader Core
submission checks and independent library publication remain pending.

Attach `dist/schluter.zip` to the prerelease. Its SHA256 is:

`8e0ec9a4949553e0323b538ca855029d0a7cb70f356ca8df4350076bed940714`

Follow the README for backup, migration and rollback. Setting a target retains
the existing permanent/manual behavior and disables vacation mode. Thermostat
scheduling continues independently during cloud outages.
