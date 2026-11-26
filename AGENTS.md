# Jus3D development standards

Apply these rules to all changes, including automatically generated communities, city pages, inventory listings, and future tools.

- Implement sitewide improvements in shared components, styles, or source generators, not individual generated pages. When separate templates remain, update and test every applicable template; prefer consolidating shared markup and behavior without disrupting inventory.
- Preserve the approved navy/gold design, responsive navigation, contact controls, typography, search panel, inventory count and freshness timestamp, right-aligned prices, status badges, centered specification icons, rounded cards, and complete property details controls where data exists. New tools inherit the shared design and navigation; do not force irrelevant controls onto unrelated pages.
- Keep stable property and community identifiers in structured data or data attributes, independent of visible labels. Never infer identity from presentation text. Preserve uncertainty warnings, held-removal safeguards, pricing disclaimers, canonical URLs, and source verification.
- Automatic community creation, retirement, restoration and inventory refresh must use current source templates and shared assets. Do not edit generated output as the permanent fix. Preserve existing SEO and nearby alternatives for retired communities.
- Before merging changes, inspect affected consumers and add targeted regression coverage for the actual changed behavior. Test representative existing and synthetic newly generated communities, desktop Chromium and mobile WebKit, including property details, search interactions, card alignment, banner contrast, and freshness behavior as applicable. Verify deployment identity and full regression results before declaring completion. Distinguish visible tour rendering from interactive playback; never claim unverified provider behavior.
- Preserve existing functionality and avoid unrelated changes. Document exceptions and unresolved verification explicitly. Do not introduce new features until requested regression gates are satisfied.

These are development requirements, not a claim that all existing components are already consolidated or that all listed tests already exist.

## Efficient delivery
Batch related changes into one atomic commit or PR before production publication. Live deployment regressions may cancel superseded runs for the same branch; preserve independent manual checks and never cancel inventory writes or active Pages publication merely to save time. Keep inventory refresh and generated pages on the current templates. Audit legacy files against actual build, runtime, workflow and recovery dependencies before removal; do not delete the inventory source or fallback safeguards. Use targeted checks for edits and retain full scheduled coverage.

## Inventory refresh recovery and next work
- Correct hourly refresh validation for current community photo hero (implemented; verify successful scheduled/push refresh and publication).
- Verify generated community pages inherit current templates, including banner, listing cards and property controls.
- Validate reusable repository cleanup guard; complete dependency review before deleting legacy code.
- Consolidate shared listing cards, then search and property details; preserve inventory identity and uncertainty safeguards.
- Do not begin Intelligent Home Finder until these gates are verified.

## Regression efficiency
Documentation-only and standalone preflight/cleanup-guard edits do not deploy. Scheduled browser regressions run daily, staggered at 08:00–08:35 UTC. Keep deployment-triggered checks until a verified change classifier can safely select affected tests; unknown changes must fail open to full coverage. Never infer a successful test from cancellation. Independent development may proceed against the last verified baseline.
