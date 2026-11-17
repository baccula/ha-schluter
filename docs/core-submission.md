# Preparing the update for Core

This is an update to the existing `schluter` integration, not a new integration
submission. Keep its domain and serial identities. Do not submit the custom
integration's `_vendor` tree to Core.

Before submission:

1. Finish the hardware acceptance checklist and address any observed API variants.
2. Publish the independently versioned `schluter_wifi` library from this public
   repository through a tagged CI release to PyPI (wheel and source distribution).
   Configure PyPI Trusted Publishing; do not place credentials in source or chat.
   Verify the final package name is available and update the Core requirement if
   the published name/version differs. The prepared pin is not yet published.
3. Rebase an unsubmitted working branch onto current upstream `dev`, rerun the
   targeted tests, hassfest, requirements generation, and repository checks.
   Do not amend or rebase commits once an actual review PR has been opened.
4. Prepare the accompanying Home Assistant documentation update using the README
   as the functional source, including YAML migration and permanent mode behavior.
   Existing Schluter brands can be retained.
5. Review every rule in `quality_scale.yaml` against measured evidence and the
   final documentation. Request Silver only when all rules are satisfied.
6. The human contributor must review and understand the code and PR description
   before submitting. This is required by Core's `AGENTS.md` and
   [Open Home Foundation AI policy](https://contributors.home-assistant.io/start/ai-policy/).
   No upstream issues, PRs, or comments are automatically posted by this task.

The original code owner remains in the proposed Core manifest; @baccula is added
as the maintainer who explicitly accepted responsibility for this work. The
Marketplace candidate lists only @baccula, and does not imply that the original
owner maintains that release.
