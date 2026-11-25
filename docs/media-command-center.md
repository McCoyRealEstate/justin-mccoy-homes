# Media Command Center — implementation specification

## Access and scope
First release is an operator report in GitHub Actions artifacts, not a public administrative page. No customer information, credentials, authentication tokens, or internal Lennar records. A future authenticated UI requires an explicit access-control design; obscured URLs are not authentication.

## Inputs
- Published verified-homepage.json: homes, community and collection identity.
- inventory-freshness.json: refresh time, source hash and held removals.
- virtual-tours.json: link coverage, not playback.
- photo-coverage.json: provenance coverage, not visual accuracy.
- virtual-tour-audit.json: dated automated outcomes and separately recorded manual evidence.
- inventory and mortgage regression: ownership fields and amenity gaps.
- build-version.json: actual deployed source and run identity.

## Reporting
Show source timestamps, total homes, communities, missing media, unresolved availability, ownership field coverage, missing amenities, automated tour results and manual observations separately. A missing or stale source must be labeled unavailable or stale, never silently represented as zero or verified. Do not infer sold status from fetch failures. Distinguish listing-specific and reference media. Do not publish incentives, commission or policy claims from this report.

## Acceptance
Read-only; no modification of inventory or tours. Validate exact lot identity, report unknown fields, preserve audit history, and test output against live published data. No public administrative UI until access requirements are agreed.
