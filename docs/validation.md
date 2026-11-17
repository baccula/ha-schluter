# Validation status

Release candidate **0.1.0rc2** prepared after successful home testing of rc1.
See the [home acceptance update](acceptance.md#home-acceptance-update).

- Core tests on Home Assistant 2026.11.1 / Python 3.14.10: 28 passed, 100% line and branch coverage of the integration modules.
- Packaged integration and bundled client: 79 tests passed; 16 additional diagnostic tests passed (95 total in the combined run). Integration modules have 100% coverage; bundled client has 99%. Config flow has 100% coverage.
- Fresh-session rejection is covered through the real client and HA scheduler both during startup (multiple setup retries) and during normal polling. Both recover after a later successful read without restarting HA or requesting a password change.
- Targeted Ruff and hassfest checks passed for Core and custom packages. Custom-domain collision warning is expected for the agreed replacement installation.
- Standalone client wheel and source distribution built successfully.
- Five test warnings originate from upstream Home Assistant/aiohttp and backoff deprecations, not integration failures.
- Repository-wide checks are not green: full setup encountered a missing autoconf dependency building DTLSSocket; the earlier full hassfest run encountered missing hassil (now installed); full mypy reported duplicate hass_dict.py/.pyi modules; pylint also failed in the repository-wide run; the identified Schluter-specific findings now pass targeted pylint. Generated-file formatting changes were incorporated. These broader checks must be completed before upstream submission.
- GitHub-hosted validation passed on the uploaded candidate: Core tests, package tests, diagnostic tests, lint, targeted metadata validation, package build, and the standalone hassfest action. Evidence: https://github.com/baccula/ha-schluter/actions/runs/44184518459. Marketplace release validation runs after publication. The Core branch is available at baccula/core, codex/schluter-modernization.
- The maintainer confirmed automatic recovery without HA restart/reload on November 12, then stable operation beyond 48 hours, working temperature control and existing automations on November 17. These are user-reported results on rc1. The agent has not accessed the real account or changed heating settings.
- The standalone schluter-wifi package is not published on PyPI; publication is required before submitting the Core dependency change.

The custom ZIP is self-contained and can be installed manually for acceptance testing. An official Silver tier and production readiness are not claimed yet.

The integration-specific pylint findings were resolved: reauthentication accepts
HA's Mapping input type, user flows start at their actual initial form, and
error-path tests demonstrate successful completion after correction.

Rc2 archive verification passed (14 files, valid ZIP, correct manifest version).
Locally verified archive SHA256: `66089389d9726bc19285c3689b481daafacfc02fb8be89d6630942f23e0a7b40`.
Targeted Core and custom-package hassfest both report zero invalid integrations.
The maintainer created `baccula/ha-schluter` on November 17 and approved
Apache-2.0 for the integration. The prepared source is now on its main branch.

Focused mypy (`--follow-imports=silent`) passes all five integration source
modules after removal of an invalid override marker on the dynamic reauth step.
Workflow security audit (zizmor) reports no findings, with 12 suppressions.
