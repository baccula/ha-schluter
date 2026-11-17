# Source and dependencies

The integration derives from `home-assistant/core`, tag `2026.11.1`,
`homeassistant/components/schluter`, under Apache-2.0. The upstream source is
preserved in the Core fork; the packaging script changes imports and metadata
for a self-contained custom integration. See `LICENSE`.

The standalone `schluter_wifi` client is developed in `library/`, under MIT. Its
protocol and temperature rounding are based on `prairieapps/py-schluter` 0.1.7
(MIT). The original copyright notice is preserved in `library/LICENSE`.
The package includes an exact source copy at
`custom_components/schluter/_vendor/schluter_wifi` so installation does not depend
on an unpublished package. It uses Home Assistant's existing aiohttp dependency.

Before Core submission, publish the client as a separate versioned PyPI source
distribution and wheel from a tagged public repository through CI. The Core
implementation imports `schluter_wifi` directly and must not include vendored
protocol code. Package version 0.1.0 is a preparation target, not a claim that
the package has already been published.

The icon is the existing Schluter icon from
`home-assistant/brands/core_integrations/schluter/icon.png`. Schluter branding
identifies the supported product and does not imply manufacturer endorsement.
