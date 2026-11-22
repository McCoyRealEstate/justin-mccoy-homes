#!/usr/bin/env python3
"""Import Lennar Orlando public inventory with fail-closed validation.

The source contains a communityHeader div immediately before each communitySection
containing a table; headings are not h1/h2/h3 elements.
"""
import datetime as dt
import json
import pathlib
import re
import sys
from collections import Counter

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent
URL = 'https://www.lennar.com/new-homes/florida/orlando/promo/olhlen_nhc_inventory?print=true'
PAGE = ROOT / 'index.html'
SNAPSHOT = ROOT / 'data' / 'inventory.json'
MIN_ROWS = 50


def parse_report(html):
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    skipped = []
    tables = soup.find_all('table')
    for table_number, table in enumerate(tables, 1):
        section = table.find_parent('div', class_=lambda c: bool(c) and 'communitySection' in c)
        if section is None:
            skipped.append(f'Table {table_number}: no communitySection parent')
            continue
        header = section.find_previous_sibling('div', class_=lambda c: bool(c) and 'communityHeader' in c)
        if header is None:
            skipped.append(f'Table {table_number}: no preceding communityHeader sibling')
            continue
        heading = header.get_text(' ', strip=True)
        if ' | ' not in heading:
            skipped.append(f'Table {table_number}: unexpected header {heading[:100]!r}')
            continue
        collection, location = heading.split(' | ', 1)
        city_match = re.search(r',\s*([^,]+),\s*FL\s*\d{5}\b', location, re.I)
        if not city_match:
            skipped.append(f'Table {table_number}: no city in {heading[:100]!r}')
            continue
        city = city_match.group(1).strip()
        rows = table.find_all('tr')
        if not rows:
            skipped.append(f'Table {table_number}: empty table')
            continue
        labels = [x.get_text(' ', strip=True).casefold() for x in rows[0].find_all(['th', 'td'])]
        expected = ['address', 'homesite', 'plan', 'beds/bath', 'sq ft', 'availability', 'price']
        if len(labels) < 7 or any(e not in label for e, label in zip(expected, labels[:7])):
            skipped.append(f'Table {table_number}: unexpected columns {labels!r}')
            continue
        for row_number, row in enumerate(rows[1:], 2):
            cells = [c.get_text(' ', strip=True) for c in row.find_all(['td', 'th'])]
            if not cells:
                continue
            if len(cells) < 7:
                skipped.append(f'Table {table_number}, row {row_number}: only {len(cells)} cells')
                continue
            address, lot, plan, bedbath, sqft_text, availability, price_text = cells[:7]
            amounts = [int(x.replace(',', '')) for x in re.findall(r'\$\s*([\d,]+)', price_text)]
            bed_bath = re.match(r'\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)', bedbath)
            sqft_match = re.search(r'([\d,]+)\s*(?:ft|sq)', sqft_text, re.I)
            if not sqft_match:
                sqft_match = re.search(r'[\d,]+', sqft_text)
            if not (address and lot and plan and bed_bath and sqft_match and amounts):
                skipped.append(f'Table {table_number}, row {row_number}: invalid listing fields')
                continue
            listings.append({
                'address': address.strip(), 'lot': lot.strip().lstrip('#'),
                'plan': plan.strip(), 'beds': int(float(bed_bath.group(1))),
                'baths': float(bed_bath.group(2)),
                'sqft': int(sqft_match.group(1).replace(',', '') if sqft_match.lastindex else sqft_match.group().replace(',', '')),
                'availability': availability.strip(), 'price': amounts[0],
                'original_price': max(amounts), 'community': collection.strip(), 'city': city,
            })
    return listings, skipped, len(tables)


def main():
    response = requests.get(URL, timeout=40, headers={'User-Agent': 'Mozilla/5.0'})
    response.raise_for_status()
    listings, skipped, table_count = parse_report(response.text)
    print(f'HTTP status: {response.status_code}', flush=True)
    print(f'Inventory tables: {table_count}', flush=True)
    print(f'Parsed listings: {len(listings)}', flush=True)
    print(f'Collections with listings: {len(set(x["community"] for x in listings))}', flush=True)
    for msg in skipped[:15]:
        print('SKIPPED:', msg, flush=True)
    if len(listings) < MIN_ROWS:
        raise RuntimeError(f'Parsed only {len(listings)} rows; refusing to replace inventory')
    if skipped:
        raise RuntimeError(f'{len(skipped)} table/row parsing issues; refusing partial inventory publication')
    keys = [(x['community'].casefold(), x['address'].casefold(), x['lot']) for x in listings]
    if len(keys) != len(set(keys)):
        raise RuntimeError('Duplicate community/address/homesite combinations; refusing to publish')

    page = PAGE.read_text(encoding='utf-8')
    marker = 'const D = '
    if marker not in page:
        raise RuntimeError('Website data marker not found; refusing to modify HTML')
    start = page.index(marker) + len(marker)
    old, end = json.JSONDecoder().raw_decode(page[start:])
    existing_communities = list(old['c'])
    by_name = {c['n'].casefold(): c for c in existing_communities}
    old_homes = {(h.get('a', '').casefold(), h.get('cm')): h for h in old['h']}
    communities, homes, active_ids = [], [], set()
    used_ids = {c['id'] for c in existing_communities}
    for item in listings:
        # Preserve collections as distinct names; do not merge Ascent and Estate.
        name = item['community']
        c = by_name.get(name.casefold())
        if c is None:
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            if slug in used_ids:
                raise RuntimeError(f'Community ID collision: {name} / {slug}')
            used_ids.add(slug)
            c = {'id': slug, 'n': name, 'c': item['city'], 'hoa': None, 'tax': None,
                 'url': 'https://www.lennar.com/new-homes/florida/orlando'}
            by_name[name.casefold()] = c
        if c['id'] not in active_ids:
            communities.append(c)
            active_ids.add(c['id'])
        prior = old_homes.get((item['address'].casefold(), c['id']), {})
        avail = item['availability'].lower()
        status = 'M' if 'move-in ready' in avail else 'S' if 'coming soon' in avail else 'U'
        homes.append({'a': item['address'], 's': status, 'p': item['price'],
                      'w': item['original_price'], 'bd': item['beds'], 'ba': item['baths'],
                      'sq': item['sqft'], 'g': prior.get('g', 0), 'pl': item['plan'],
                      'cm': c['id'], 'lot': item['lot'], 'miss': 0,
                      'avail': item['availability'], 'verified': True})

    now = dt.datetime.now(dt.timezone.utc)
    payload = json.dumps({'c': communities, 'h': homes}, separators=(',', ':'), ensure_ascii=False)
    updated_page = page[:start] + payload + page[start + end:]
    updated_page = re.sub(r'const IMPORTED = "[^"]*";', f'const IMPORTED = "{now:%Y-%m-%dT%H:%M:%SZ}";', updated_page, count=1)
    updated_page = re.sub(r'const UPDATED = "[^"]*";', f'const UPDATED = "{now:%B %d, %Y}";', updated_page, count=1)
    snapshot = {'source': URL, 'checked_at_utc': now.isoformat(), 'verified_count': len(homes),
                'community_count': len(communities), 'listings': listings}
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    # Prepare all content before replacing the live website file.
    snapshot_temp = SNAPSHOT.with_suffix('.json.tmp')
    page_temp = PAGE.with_suffix('.html.tmp')
    snapshot_temp.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8')
    page_temp.write_text(updated_page, encoding='utf-8')
    snapshot_temp.replace(SNAPSHOT)
    page_temp.replace(PAGE)
    print(f'VERIFIED: {len(homes)} homes across {len(communities)} collections')
    print('No unverified carryover listings published.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'INVENTORY REFRESH FAILED: {exc}', file=sys.stderr)
        sys.exit(1)
