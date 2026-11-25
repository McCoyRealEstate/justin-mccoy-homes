# Jus3D.com — Central Florida new homes

Customer-facing inventory and community website maintained for Justin McCoy. Public Lennar sources are used for inventory; this repository is not an official Lennar system.

## Production architecture

- `index.html`: inventory source and legacy baseline; do not delete.
- `homepage-v2-preview.html`: current production homepage template despite its historical filename.
- `build_lennar_preview.py`, `verify_lennar_preview.py`, `lennar_phase6_dry_run.py`, `lennar_phase8_finalize.py`: controlled inventory refresh and validation.
- `generate_community_pages.py`, `generate_city_experience.py`, `generate_property_previews.py`: community, area and property presentation.
- `build_floorplan_library.py`: verified media enrichment and explicitly approved reference exceptions.
- `assets/ownership-details.js`: property amenities, ownership costs, mortgage estimates and media viewer.
- `data/inventory-freshness.json`: refresh timestamp and unresolved listing exceptions.
- `data/manual-tour-verifications.json`: manually observed tour outcomes.

## Automation

The hourly refresh workflow is `.github/workflows/lennar-phase8-auto-refresh.yml`. Publication requires the configured enable flag and successful validation. The Pages production workflow assembles and publishes the website and checks the live build identity. Live smoke, mobile floor plan, inventory/mortgage and virtual tour workflows provide additional regression coverage.

A successful workflow does not establish that every source fact or third-party tour is independently verified. Preserve uncertainty labels and do not infer that a failed source request means a home sold.

## Maintenance

Review Actions logs and artifacts before changing production. Keep existing media and source identity safeguards, avoid unverified fee or incentive claims, and preserve rollback history. Do not remove legacy-named files solely because of their names. Check references and test changes before retiring workflows or assets.

See [accuracy and compliance safeguards](docs/data-accuracy-and-compliance.md) and [product roadmap](docs/product-roadmap.md).
