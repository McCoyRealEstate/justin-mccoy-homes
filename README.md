# Justin McCoy Homes — Version 6 (test-first)

## Files
- `index.html`: exact `public-page.html` from the supplied ZIP. No design edits.
- `laptop-page.html`: original supplied laptop snapshot, for reference only; do not publish it.
- `update_inventory.py`: conservative updater. Default is **dry run**.
- `update.yml`: manual GitHub Actions workflow; initially **no schedule** until verified.

## GitHub installation
1. Keep your GitHub backup. Upload `index.html` to repository root (this restores the Claude design).
2. Upload `update_inventory.py` to repository root.
3. Replace `.github/workflows/update.yml` with the provided `update.yml` contents.
4. Run workflow with `publish=false` and inspect the output. A green result means code executed, **not** that inventory matches Lennar. If any error, do not publish.
5. Only after reviewing the output, run with `publish=true`.

## Important limitations
- Lennar's printable report can omit individual homesite links; this importer **refuses to add** a new home without a validated direct homesite link. It will report the issue instead of inventing links.
- Coming Soon listings are preserved because plain HTTP cannot reliably expand Lennar's View More interface. They must be audited by the laptop browser process.
- Missing available homes are checked individually. Removal is limited to 15 per run; for additional protection, removal proposals require explicit `--allow-deletions` and will otherwise block publication.
- `IMPORTED` is never changed by the updater; optional laptop synchronization can be tested locally with `--laptop laptop-page.html` (but do not overwrite the original laptop copy).
- Photos and image maps are never edited by the updater.
- No schedule is enabled until live data and full listing coverage have been verified. After approval, schedule can be added; note GitHub cron uses UTC and daylight saving time must be accounted for.
