# Silver requirements and evidence

This is a **candidate self-assessment**, not an official tier for a custom
integration. The proposed Core manifest requests Silver; upstream review,
dependency publication and documentation submission remain Core submission
gates. Home acceptance results are recorded in `acceptance.md`. Core's quality scale file is included in the prepared
patch. The Marketplace manifest intentionally contains no quality-tier claim.

| Rules | Evidence |
| --- | --- |
| GUI configuration, unique entry, test before configure | Account flow validates login and a thermostat fetch; normalized email prevents duplicates; all config-flow code exercised. Noninteractive YAML import creates a retryable entry during outages. |
| Test before setup | `async_config_entry_first_refresh` uses HA's retry and auth lifecycle. |
| Runtime data and common modules | Typed config-entry coordinator; constants and flow in dedicated modules. |
| Appropriate polling and parallel updates | Shared 60-second account poll, serialized client requests, `PARALLEL_UPDATES = 1`, server retry delay honored. |
| Unique IDs and entity names | Legacy serial IDs retained; device registry owns the room name; `has_entity_name` and `name=None`. |
| Entity event setup and unloading | Coordinator listeners are registered with config-entry unload callbacks; reload/unload tests verify polling stops and no duplicates appear. |
| Action exceptions | Failed and ambiguous writes surface translated HA errors; no optimistic target update. |
| Entity unavailable | Cloud errors, missing device, and device offline all produce unavailable; later scheduled polls restore it. |
| Log when unavailable | Coordinator logs cloud transitions once; entity logs offline/missing transitions and restoration. |
| Reauthentication | Only rejected login credentials trigger reauthentication; the original entry reloads after password validation. |
| Integration owner | @baccula explicitly accepted ongoing maintenance. |
| Tests | Core lifecycle, state/action, migration, scheduled recovery, flow, and real-client HTTP-boundary tests; standalone client tests exercise the protocol and retries. Per-module coverage is measured, not inferred from test count. |
| Dependency transparency | Source, licenses, and provenance in `THIRD_PARTY.md`; client source and package metadata in `library/`. Core requires publication before submission. |
| Brands | Existing Schluter brand artwork; custom release includes the icon with source attribution. |
| High-level description, installation/removal, setup parameters | README and prepared Home Assistant documentation cover account prerequisites, email/password, migration, setup, removal, and rollback. |
| Integration-specific actions, conditions, triggers | Exempt: none are added. Standard climate actions are retained. |
| Configuration parameters | Exempt: no options are exposed. The fixed poll interval is documented. |

The detailed coverage and validation results are recorded in `validation.md`.
