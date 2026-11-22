#!/usr/bin/env python3
"""Fail-closed Lennar public report importer with response diagnostics."""
import datetime as dt
import json
import pathlib
import re
import sys
import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent
URL = 'https://www.lennar.com/new-homes/florida/orlando/promo/olhlen_nhc_inventory?print=true'
PAGE = ROOT / 'index.html'
MIN_ROWS = 50


def parse_report(html):
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    community = city = ''
    for node in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'table']):
        if node.name != 'table':
            text = node.get_text(' ', strip=True)
            if ' | ' in text and re.search(r',\s*FL\s*\d{5}', text):
                community, loc = text.split(' | ', 1)
                match = re.search(r',\s*([^,]+),\s*FL\s*\d{5}', loc)
                city = match.group(1).strip() if match else ''
            continue
        rows = node.find_all('tr')
        if not rows:
            continue
        headers = [cell.get_text(' ', strip=True).lower() for cell in rows[0].find_all(['th', 'td'])]
        if not any('homesite' in h for h in headers):
            continue
        for row in rows[1:]:
            cells = [cell.get_text(' ', strip=True) for cell in row.find_all(['td', 'th'])]
            if len(cells) < 7 or not community:
                continue
            addr, lot, plan, bedbath, sqft, availability, price = cells[:7]
            amounts = [int(n.replace(',', '')) for n in re.findall(r'\$([\d,]+)', price)]
            numbers = re.findall(r'\d+(?:\.\d+)?', bedbath)
            if len(numbers) < 2 or not amounts or not addr or not plan:
                continue
            listings.append(dict(
                address=addr.strip(), lot=lot.strip().lstrip('#'), plan=plan.strip(),
                beds=int(float(numbers[0])), baths=float(numbers[1]),
                sqft=int(re.sub(r'\D', '', sqft) or '0'), availability=availability.strip(),
                price=amounts[0], original_price=max(amounts),
                community=community.strip(), city=city,
            ))
    return listings


def main():
    response = requests.get(URL, timeout=40, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; inventory-check/1.0)'
    })
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    print('HTTP status:', response.status_code, flush=True)
    print('Final URL:', response.url, flush=True)
    print('Content type:', response.headers.get('Content-Type'), flush=True)
    print('Response length:', len(response.text), flush=True)
    print('HTML tables:', len(soup.find_all('table')), flush=True)
    print('Contains Homesite:', 'homesite' in response.text.lower(), flush=True)
    print('Contains Meadow Pointe:', 'meadow pointe' in response.text.lower(), flush=True)
    print('Page title:', soup.title.get_text(' ', strip=True)[:120] if soup.title else '(none)', flush=True)

    listings = parse_report(response.text)
    print('Parsed listings:', len(listings), flush=True)
    if len(listings) < MIN_ROWS:
        raise RuntimeError(f'Parsed only {len(listings)} rows; refusing to replace inventory')
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
        name = item['community'].split(' - ')[0].strip()
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
        homes.append(dict(
            a=item['address'], s=status, p=item['price'], w=item['original_price'],
            bd=item['beds'], ba=item['baths'], sq=item['sqft'], g=prior.get('g', 0),
            pl=item['plan'], cm=c['id'], lot=item['lot'], miss=0,
            avail=item['availability'], verified=True,
        ))

    active_ids = {h['cm'] for h in homes}
    communities = [c for c in communities if c['id'] in active_ids]
    updated = dt.datetime.now(dt.timezone.utc)
    snapshot = dict(source=URL, checked_at_utc=updated.isoformat(),
                    verified_count=len(homes), community_count=len(communities), listings=listings)
    payload = json.dumps(dict(c=communities, h=homes), separators=(',', ':'), ensure_ascii=False)
    html = html[:start] + payload + html[start + end:]
    html = re.sub(r'const IMPORTED = "[^"]*";',
                  f'const IMPORTED = "{updated:%Y-%m-%dT%H:%M:%SZ}";', html, count=1)
    html = re.sub(r'const UPDATED = "[^"]*";',
                  f'const UPDATED = "{updated:%B %d, %Y}";', html, count=1)

    data_dir = ROOT / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / 'inventory.json').write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    PAGE.write_text(html, encoding='utf-8')
    print(f'VERIFIED: {len(homes)} homes across {len(communities)} active communities')
    print(f'SOURCE: {URL}')
    print(f'CHECKED UTC: {updated.isoformat()}')
    print('No unverified carryover listings published.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'INVENTORY REFRESH FAILED: {exc}', file=sys.stderr)
        sys.exit(1)
