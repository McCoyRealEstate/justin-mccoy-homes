#!/usr/bin/env python3
"""Import Lennar Orlando public print inventory, refusing incomplete updates."""
import datetime as dt
import json
import pathlib
import re
import sys
import tempfile
import os
import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent
URL = 'https://www.lennar.com/new-homes/florida/orlando/promo/olhlen_nhc_inventory?print=true'
PAGE = ROOT / 'index.html'
MIN_ROWS = 50
MIN_COLLECTIONS = 15
HEADER_CLASS = re.compile(r'HomesOfTheWeekTablePrint_communityHeader')


def parse_header(header):
    """Get collection and city from full header, not its address-only child."""
    text = header.get_text(' ', strip=True)
    # The site renders 'Community – Collection | Street, City, FL ZIP'.
    parts = re.split(r'\s*\|\s*', text, maxsplit=1)
    if len(parts) != 2 or not parts[0].strip():
        return None
    name, location = parts[0].strip(), parts[1]
    city_match = re.search(r',\s*([^,|]+),\s*FL\s*\d{5}(?:-\d{4})?\b', location, re.I)
    if not city_match:
        return None
    return name, city_match.group(1).strip()


def parse_report(html):
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    print('HTTP inventory tables:', len(tables), flush=True)
    listings = []
    rejected = []
    for idx, table in enumerate(tables, 1):
        rows = table.find_all('tr')
        if not rows:
            continue
        columns = [c.get_text(' ', strip=True).casefold() for c in rows[0].find_all(['th', 'td'])]
        if not any('homesite' in c for c in columns):
            continue
        # find_previous() traverses the document, including outside table parents.
        # This matches the site's separate communityHeader div preceding each table.
        header = table.find_previous(lambda tag: tag.name == 'div' and
                                     any(HEADER_CLASS.search(cls) for cls in tag.get('class', [])))
        parsed = parse_header(header) if header else None
        if not parsed:
            sample = header.get_text(' ', strip=True)[:180] if header else '(no header found)'
            rejected.append(f'Table {idx}: invalid community header: {sample}')
            continue
        community, city = parsed
        for row in rows[1:]:
            cells = [c.get_text(' ', strip=True) for c in row.find_all(['td', 'th'])]
            if len(cells) < 7:
                continue
            addr, lot, plan, bedbath, sqft, availability, price = cells[:7]
            amounts = [int(x.replace(',', '')) for x in re.findall(r'\$\s*([\d,]+)', price)]
            nums = re.findall(r'\d+(?:\.\d+)?', bedbath)
            sqft_digits = re.sub(r'\D', '', sqft)
            if not (addr and plan and len(nums) >= 2 and amounts and sqft_digits):
                rejected.append(f'Table {idx}: invalid listing row: {cells[:7]!r}'[:240])
                continue
            listings.append(dict(address=addr.strip(), lot=lot.strip().lstrip('#'),
                                 plan=plan.strip(), beds=int(float(nums[0])),
                                 baths=float(nums[1]), sqft=int(sqft_digits),
                                 availability=availability.strip(), price=amounts[0],
                                 original_price=max(amounts), community=community, city=city))
    print('Parsed listings:', len(listings), flush=True)
    print('Parsed collections:', len({x['community'] for x in listings}), flush=True)
    for msg in rejected[:12]:
        print('REJECTED:', msg, flush=True)
    if rejected:
        raise RuntimeError(f'{len(rejected)} table/row parsing errors; refusing partial publication')
    return listings


def main():
    response = requests.get(URL, timeout=40, headers={'User-Agent': 'Mozilla/5.0'})
    response.raise_for_status()
    print('HTTP status:', response.status_code, flush=True)
    listings = parse_report(response.text)
    if len(listings) < MIN_ROWS:
        raise RuntimeError(f'Parsed only {len(listings)} rows; refusing to replace inventory')
    if len({x['community'] for x in listings}) < MIN_COLLECTIONS:
        raise RuntimeError('Too few collections parsed; refusing to replace inventory')
    keys = [(x['community'].casefold(), x['address'].casefold(), x['lot']) for x in listings]
    if len(set(keys)) != len(keys):
        raise RuntimeError('Duplicate community/address/homesite combinations')

    html = PAGE.read_text(encoding='utf-8')
    marker = 'const D = '
    start = html.index(marker) + len(marker)
    old, end = json.JSONDecoder().raw_decode(html[start:])
    communities = list(old['c'])
    by_name = {c['n'].casefold(): c for c in communities}
    previous = {(h.get('a', '').casefold(), h.get('cm')): h for h in old['h']}
    homes = []
    used_ids = {c['id'] for c in communities}
    for item in listings:
        name = item['community'].strip()  # Keep distinct collections distinct.
        c = by_name.get(name.casefold())
        if c is None:
            base = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'collection'
            slug = base
            i = 2
            while slug in used_ids:
                slug = f'{base}-{i}'
                i += 1
            used_ids.add(slug)
            c = dict(id=slug, n=name, c=item['city'], hoa=None, tax=None,
                     url='https://www.lennar.com/new-homes/florida/orlando')
            communities.append(c)
            by_name[name.casefold()] = c
        prior = previous.get((item['address'].casefold(), c['id']), {})
        availability = item['availability'].casefold()
        status = 'M' if 'move-in ready' in availability else 'S' if 'coming soon' in availability else 'U'
        homes.append(dict(a=item['address'], s=status, p=item['price'], w=item['original_price'],
                          bd=item['beds'], ba=item['baths'], sq=item['sqft'], g=prior.get('g', 0),
                          pl=item['plan'], cm=c['id'], lot=item['lot'], miss=0,
                          avail=item['availability'], verified=True))
    active_ids = {h['cm'] for h in homes}
    communities = [c for c in communities if c['id'] in active_ids]
    now = dt.datetime.now(dt.timezone.utc)
    snapshot = dict(source=URL, checked_at_utc=now.isoformat(), verified_count=len(homes),
                    community_count=len(communities), listings=listings)
    payload = json.dumps(dict(c=communities, h=homes), separators=(',', ':'), ensure_ascii=False)
    updated_html = html[:start] + payload + html[start + end:]
    updated_html = re.sub(r'const IMPORTED = "[^"]*";', f'const IMPORTED = "{now:%Y-%m-%dT%H:%M:%SZ}";', updated_html, count=1)
    updated_html = re.sub(r'const UPDATED = "[^"]*";', f'const UPDATED = "{now:%B %d, %Y}";', updated_html, count=1)
    # Stage files first. The workflow only commits after the importer succeeds.
    data_dir = ROOT / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = data_dir / 'inventory.json'
    snapshot_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8')
    PAGE.write_text(updated_html, encoding='utf-8')
    print(f'VERIFIED: {len(homes)} homes across {len(communities)} collections', flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'INVENTORY REFRESH FAILED: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
