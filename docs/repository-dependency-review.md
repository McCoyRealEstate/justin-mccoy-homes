# Repository dependency review

## Protected production chain
Hourly refresh: build_lennar_preview.py → verify_lennar_preview.py → lennar_phase6_dry_run.py → lennar_phase8_finalize.py → validate_photo_hierarchy.py → prepare_city_inventory.py → generate_local_pages.py and generate_community_pages.py. The refresh commits inventory and generated pages only after validation. Pages production rebuilds presentation from current templates and verifies deployed identity. Historical filenames are not evidence of obsolescence.

## Manual diagnostics retained
The cloud probe, full import audit, Phase 5 verification, Phase 6 dry run/photo fix, photo sample test and unpublished preview workflows are manual-only. They do not slow ordinary deployments. Retain until recovery value and all references have been reviewed.

## Cleanup guard
The original cleanup workflow hard-coded eight already-retired preview files. Replace that one-time assertion with protected-source and deleted-path checks, plus existing syntax checks. Exact textual references do not prove dynamic dependencies are absent. Review runtime references, recovery use and generated outputs before deletion. No production source or diagnostic has been removed in this batch.

## Next consolidation
Move shared presentation out of separate homepage/community implementations incrementally; test synthetic new and restored communities and actual property details before retiring old code.
