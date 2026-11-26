# Jus3D development standards

Apply these rules to all changes, including automatically generated communities, city pages, inventory listings, and future tools.

- Implement sitewide improvements in shared components, styles, or source generators, not individual generated pages. When separate templates remain, update and test every applicable template; prefer consolidating shared markup and behavior without disrupting inventory.
- Preserve the approved navy/gold design, responsive navigation, contact controls, typography, search panel, inventory count and freshness timestamp, right-aligned prices, status badges, centered specification icons, rounded cards, and complete property details controls where data exists. New tools inherit the shared design and navigation; do not force irrelevant controls onto unrelated pages.
- Keep stable property and community identifiers in structured data or data attributes, independent of visible labels. Never infer identity from presentation text. Preserve uncertainty warnings, held-removal safeguards, pricing disclaimers, canonical URLs, and source verification.
- Automatic community creation, retirement, restoration and inventory refresh must use current source templates and shared assets. Do not edit generated output as the permanent fix. Preserve existing SEO and nearby alternatives for retired communities.
- Before merging changes, inspect affected consumers and add targeted regression coverage for the actual changed behavior. Test representative existing and synthetic newly generated communities, desktop Chromium and mobile WebKit, including property details, search interactions, card alignment, banner contrast, and freshness behavior as applicable. Verify deployment identity and full regression results before declaring completion. Distinguish visible tour rendering from interactive playback; never claim unverified provider behavior.
- Preserve existing functionality and avoid unrelated changes. Document exceptions and unresolved verification explicitly. Do not introduce new features until requested regression gates are satisfied.

These are development requirements, not a claim that all existing components are already consolidated or that all listed tests already exist.
