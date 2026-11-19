# Justin McCoy — Lennar Inventory Website V2

Open `index.html` to preview the existing responsive website with its current embedded inventory snapshot, search, filters and favorites.

## Automated updates

`update_inventory.py` fetches the public Lennar Orlando printable inventory and updates the embedded inventory dataset in `index.html`. It refuses to overwrite the site if it parses fewer than 50 listings. The GitHub Actions workflow can run daily or manually once this repository is published and Actions enabled. Scheduled workflow times are UTC and do not automatically adjust for daylight saving time.

**Important:** The updater is provided but has **not been run or verified against the live Lennar HTML in this environment**. Lennar may change its markup, block automated requests, or restrict automated use. Verify permitted access and test parsing before relying on automatic updates. The site should not be described as real-time. Existing Coming Soon entries not present in the report are retained as unverified and hidden from published pricing.

The original page's community URLs, photos, and other details remain from the uploaded snapshot; these are not independently refreshed by the updater. Prices and availability must be confirmed with Lennar. No public visitor analytics or server-side lead form storage is configured.

## Publish

Create a GitHub repository, upload this folder, enable GitHub Pages from the main branch root, and enable GitHub Actions. Test `workflow_dispatch` before depending on the schedule. For production use, review Lennar's terms and use an authorized feed if available.
