#!/usr/bin/env python3
"""Import Lennar Orlando print inventory; fail closed on structural anomalies."""
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
MIN_ROWS = 50
HEADER_CLASS = re.compile(r'communityHeader', re.I)
SECTION_CLASS = re.compile(r'communitySection', re.I)
CITY_RE = re.compile(r',\s*([^,|]+),\s*FL\s*\d{5}\b', re.I)
PRICE_RE = re.compile(r'\$\s*([\d,]+)')


def class_matches(tag, pattern):
    return bool(tag and tag.name and any(pattern.search(c) for c in tag.get('class', [])))


def header_for_table(table):
    """Find header within this section, or the nearest header earlier in document order."""
    section = table.find_parent(lambda tag: class_matches(tag, SECTION_CLASS))
    if section:
        header = section.find_previous_sibling(lambda tag: class_matches(tag, HEADER_CLASS))
        if header:
            return header
        # Some renderings wrap header and section in separate containers.
        header = section.find_previous(lambda tag: class_matches(tag, HEADER_CLASS))
        if header:
            return header
    return table.find_previous(lambda tag: class_matches(tag, HEADER_CLASS))


def parse_report(html):
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    listings = []
    rejected = []
    found_sections = set()
    for index, table in enumerate(tables, 1):
        rows = table.find_all('tr')
        if len(rows) < 2:
            rejected.append((index, 'empty table'))
            continue
        headings = [x.get_text(' ', strip=True).lower() for x in rows[0].find_all(['th', 'td'])]
        if not ('address' in headings and 'homesite' in headings and 'price' in headings):
            rejected.append((index, 'unexpected columns'))
            continue
        header = header_for_table(table)
        if header is None:
            rejected.append((index, 'community header not found'))
            continue
        heading_text = header.get_text(' ', strip=True)
        if '|' not in heading_text:
            rejected.append((index, f'header has no separator: {heading_text[:90]}'))
            continue
        community, location = [x.strip() for x in heading_text.split('|', 1)]
        match = CITY_RE.search(location)
        if not community or not match:
            rejected.append((index, f'cannot parse community/city: {heading_text[:90]}'))
            continue
        city = match.group(1).strip()
        found_sections.add(community)
        for row in rows[1:]:
            cells = [x.get_text(' ', strip=True) for x in row.find_all(['td', 'th'])]
            if len(cells) < 7:
                rejected.append((index, f'row with {len(cells)} columns'))
                continue
            address, lot, plan, bedbath, sqft, availability, price = cells[:7]
            amounts = [int(n.replace(',', '')) for n in PRICE_RE.findall(price)]
            numbers = re.findall(r'\d+(?:\.\d+)?', bedbath)
            square_feet = int(re.sub(r'\D', '', sqft) or '0')
            if not address or not plan or len(numbers) < 2 or not amounts or square_feet < 300:
                rejected.append((index, f'unparseable home row: {cells[:4]}'))
                continue
            listings.append(dict(address=address, lot=lot.lstrip('#').strip(), plan=plan,
                                 beds=int(float(numbers[0])), baths=float(numbers[1]),
                                 sqft=square_feet, availability=availability,
                                 price=amounts[0], original_price=max(amounts),
                                 community=community, city=city))
    print(f'HTTP inventory tables: {len(tables)}', flush=True)
    print(f'Parsed listings: {len(listings)}', flush=True)
    print(f'Parsed collections: {len(found_sections)}', flush=True)
    for idx, reason in rejected[:12]:
        print(f'REJECTED table {idx}: {reason}', flush=True)
    return listings, len(tables), len(found_sections), rejected


def main():
    response = requests.get(URL, timeout=40, headers={'User-Agent': 'Mozilla/5.0 (compatible; inventory-check/1.0)'})
    response.raise_for_status()
    print('HTTP status:', response.status_code, flush=True)
    listings, table_count, collection_count, rejected = parse_report(response.text)
    if len(listings) < MIN_ROWS:
        raise RuntimeError(f'Parsed only {len(listings)} rows; refusing to replace inventory')
    if collection_count < 10:
        raise RuntimeError(f'Only {collection_count} collections parsed; refusing to replace inventory')
    if any('unparseable home row' in reason or 'community header not found' in reason or 'cannot parse community/city' in reason for _, reason in rejected):
        raise RuntimeError(f'Unparsed inventory rows or missing community names detected ({len(rejected)} issues); refusing to publish')
    unique = {(x['community'].casefold(), x['address'].casefold(), x['lot']) for x in listings}
    if len(unique) != len(listings):
        raise RuntimeError('Duplicate community/address/homesite combinations; refusing to publish')
    html = PAGE.read_text(encoding='utf-8')
    marker = 'const D = '
    start = html.index(marker) + len(marker)
    old, end = json.JSONDecoder().raw_decode(html[start:])
    communities = list(old['c'])
    by_name = {c['n'].casefold(): c for c in communities}
    previous = {(h.get('a', '').casefold(), h.get('cm')): h for h in old['h']}
    homes = []
    for item in listings:
        name = item['community']  # Preserve collection names to avoid mixing separate collections.
        c = by_name.get(name.casefold())
        if c is None:
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            c = dict(id=slug, n=name, c=item['city'], hoa=None, tax=None,
                     url='https://www.lennar.com/new-homes/florida/orlando')
            communities.append(c)
            by_name[name.casefold()] = c
        prior = previous.get((item['address'].casefold(), c['id']), {})
        availability = item['availability'].lower()
        status = 'M' if 'move-in ready' in availability else 'S' if 'coming soon' in availability else 'U'
        homes.append(dict(a=item['address'], s=status, p=item['price'], w=item['original_price'],
                          bd=item['beds'], ba=item['baths'], sq=item['sqft'], g=prior.get('g', 0),
                          pl=item['plan'], cm=c['id'], lot=item['lot'], miss=0,
                          avail=item['availability'], verified=True))
    active_ids = {h['cm'] for h in homes}
    communities = [c for c in communities if c['id'] in active_ids]
    updated = dt.datetime.now(dt.timezone.utc)
    snapshot = dict(source=URL, checked_at_utc=updated.isoformat(), verified_count=len(homes),
                    community_count=len(communities), listings=listings)
    payload = json.dumps(dict(c=communities, h=homes), separators=(',', ':'), ensure_ascii=False)
    new_html = html[:start] + payload + html[start + end:]
    new_html = re.sub(r'const IMPORTED = "[^"]*";', f'const IMPORTED = "{updated:%Y-%m-%dT%H:%M:%SZ}";', new_html, count=1)
    new_html = re.sub(r'const UPDATED = "[^"]*";', f'const UPDATED = "{updated:%B %d, %Y}";', new_html, count=1)
    data_dir = ROOT / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    # Prepare both outputs before replacing either file.
    temp_html = PAGE.with_suffix('.html.tmp')
    temp_json = data_dir / 'inventory.json.tmp'
    temp_html.write_text(new_html, encoding='utf-8')
    temp_json.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8')
    temp_html.replace(PAGE)
    temp_json.replace(data_dir / 'inventory.json')
    print(f'VERIFIED: {len(homes)} homes across {len(communities)} active collections', flush=True)
    print(f'CHECKED UTC: {updated.isoformat()}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'INVENTORY REFRESH FAILED: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
