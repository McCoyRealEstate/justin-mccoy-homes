#!/usr/bin/env python3
"""Conservative Lennar Orlando inventory synchronization for the original Claude page.

Default is dry-run. Never modifies IMPORTED or the locked photo constants.
No browser automation: pages hidden behind View more cannot be verified by this script.
"""
import argparse
import copy
import datetime as dt
import json
import pathlib
import re
import sys
from collections import Counter
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent
PAGE = ROOT / 'index.html'
BASE = 'https://www.lennar.com/new-homes/florida/orlando/'
SOURCE = BASE + 'promo/olhlen_nhc_inventory'
PRINT_SOURCE = SOURCE + '?print=true'
HEADER_RE = re.compile(r'communityHeader', re.I)
LOCKED = ('IMG', 'PH', 'PLANPH', 'HIMG')
USER_AGENT = 'Mozilla/5.0 (compatible; JustinMcCoyInventoryAudit/1.0)'


def line_data(html, name):
    pattern = re.compile(r'(?m)^(const\s+' + re.escape(name) + r'\s*=\s*)')
    match = pattern.search(html)
    if not match:
        raise ValueError(f'Missing const {name}')
    value, length = json.JSONDecoder().raw_decode(html[match.end():])
    return value, (match.end(), match.end() + length)


def replace_data(html, name, value):
    _, (start, end) = line_data(html, name)
    return html[:start] + json.dumps(value, ensure_ascii=False, separators=(',', ':')) + html[end:]


def norm(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).casefold()


def lot_key(value):
    return str(value or '').strip().lstrip('#').casefold()


def address_key(value):
    return re.sub(r'[^a-z0-9]', '', norm(value))


def header_details(tag):
    # Actual print page: separate communityHeader div, with nested text nodes.
    chunks = [s.strip() for s in tag.stripped_strings if s.strip()]
    text = tag.get_text(' ', strip=True)
    match = re.search(r'\b([A-Za-z][A-Za-z .-]+),\s*FL\s*\d{5}\b', text, re.I)
    if not match:
        raise ValueError(f'Header missing Florida city: {text[:160]}')
    city = match.group(1).strip()
    # The first meaningful chunk is 'Brentwood – Ascent Collection', not the address.
    name = next((s for s in chunks if 'collection' in s.casefold()), '')
    if not name:
        name = re.split(r'\s*\|\s*', text, maxsplit=1)[0].strip()
    name = re.sub(r'\s*[|]\s*$', '', name).strip()
    if not name or re.search(r'\bFL\s*\d{5}', name, re.I):
        raise ValueError(f'Header missing community/collection: {text[:160]}')
    return name, city


def parse_price(value):
    amounts = [int(x.replace(',', '')) for x in re.findall(r'\$\s*([\d,]+)', value)]
    if not amounts:
        raise ValueError(f'Missing price: {value}')
    price = amounts[0]
    if not 100000 <= price <= 2000000:
        raise ValueError(f'Price out of range: {price}')
    # The print report commonly has current and prior price as two amounts.
    was = max(amounts) if len(amounts) > 1 else price
    badge = re.search(r'\$\s*(\d+(?:\.\d+)?)\s*([kKmM])\b', value)
    if badge and len(amounts) == 1:
        was = price + round(float(badge.group(1)) * (1000 if badge.group(2).lower() == 'k' else 1000000))
    return price, was


def parse_baths(value):
    numbers = re.findall(r'\d+(?:\.\d+)?', value)
    if len(numbers) < 2:
        raise ValueError(f'Invalid beds/baths: {value}')
    beds = int(float(numbers[0]))
    baths = float(numbers[1])
    if 'half' in value.casefold():
        # '3/2 + 1 half' = 2.5, not 2 or 1.
        baths += .5 * float(numbers[2] if len(numbers) > 2 else 1)
    return beds, baths


def status(value):
    v = norm(value)
    if 'move-in ready' in v or 'move in ready' in v:
        return 'M'
    if any(x in v for x in ('est.', 'completion', 'under construction', 'construction')):
        return 'U'
    raise ValueError(f'Unknown public inventory status: {value}')


def href_for_row(row, lot):
    for a in row.find_all('a', href=True):
        path = urlparse(urljoin(BASE, a['href'])).path
        basepath = urlparse(BASE).path
        if path.startswith(basepath) and path.rstrip('/').split('/')[-1].casefold() == lot:
            return path[len(basepath):].lstrip('/')
    return None


def fetch(session, url):
    r = session.get(url, timeout=35, allow_redirects=True)
    r.raise_for_status()
    if len(r.content) < 1500:
        raise RuntimeError(f'Suspiciously short response from {url}')
    return r


def parse_inventory(html):
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    result = []
    errors = []
    for i, table in enumerate(tables, 1):
        rows = table.find_all('tr')
        if not rows:
            continue
        headers = [norm(c.get_text(' ', strip=True)) for c in rows[0].find_all(['td', 'th'])]
        if not any('homesite' in x for x in headers):
            continue
        header = table.find_previous(lambda t: t.name == 'div' and any(HEADER_RE.search(c) for c in t.get('class', [])))
        if header is None:
            errors.append(f'Table {i}: no community header')
            continue
        try:
            collection, city = header_details(header)
        except ValueError as exc:
            errors.append(f'Table {i}: {exc}')
            continue
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'], recursive=False)
            if not cells:
                continue
            if len(cells) != 7:
                errors.append(f'Table {i}: unexpected {len(cells)} columns')
                continue
            addr, lot, plan, bb, sq, avail, price_text = [c.get_text(' ', strip=True) for c in cells]
            try:
                p, w = parse_price(price_text)
                bd, ba = parse_baths(bb)
                square = int(re.sub(r'\D', '', sq))
                if not addr or not plan or not lot_key(lot) or not 300 <= square <= 12000:
                    raise ValueError('Missing/implausible address, lot, plan, or square footage')
                result.append(dict(a=addr, lot=lot_key(lot), pl=plan, bd=bd, ba=ba,
                                   sq=square, s=status(avail), p=p, w=w,
                                   collection=collection, city=city,
                                   path=href_for_row(row, lot_key(lot))))
            except ValueError as exc:
                errors.append(f'Table {i}, {addr[:50]}: {exc}')
    if errors:
        raise RuntimeError('Incomplete report: ' + '; '.join(errors[:6]) + f' ({len(errors)} errors)')
    if len(result) < 50:
        raise RuntimeError(f'Only {len(result)} listings parsed')
    keys = [(norm(x['collection']), x['lot']) for x in result]
    if len(set(keys)) != len(keys):
        raise RuntimeError('Duplicate collection/lot in source')
    return result, len(tables)


def collection_slug(path):
    parts = str(path).strip('/').split('/')
    return '/'.join(parts[:3]) if len(parts) >= 3 else ''


def page_indicates_sold(session, path, lot):
    try:
        url = urljoin(BASE, path)
        response = fetch(session, url)
        if response.url.rstrip('/').split('/')[-1].casefold() != lot:
            return True, 'redirected away from homesite'
        soup = BeautifulSoup(response.text, 'html.parser')
        text = norm(soup.get_text(' ', strip=True))
        if re.search(r'\b(sold|no longer available)\b', text) and lot not in text:
            return True, 'sold/unavailable message'
        return False, 'homesite page still accessible; retained'
    except requests.RequestException:
        return None, 'homesite request failed'
    except RuntimeError:
        return None, 'homesite response incomplete'


def sync(html, laptop, session, *, allow_deletions=False):
    before = html
    laptop_used = False
    warnings = []
    if laptop is not None:
        local_time, _ = line_data(laptop, 'IMPORTED')
        public_time, _ = line_data(html, 'IMPORTED')
        local_dt = dt.datetime.fromisoformat(local_time.replace('Z', '+00:00'))
        public_dt = dt.datetime.fromisoformat(public_time.replace('Z', '+00:00'))
        if local_dt > public_dt:
            for key in ('IMPORTED', 'D', 'LU', *LOCKED):
                value, _ = line_data(laptop, key)
                html = replace_data(html, key, value)
            laptop_used = True
        if dt.datetime.now(dt.timezone.utc) - local_dt > dt.timedelta(hours=24):
            warnings.append('Laptop import is older than 24 hours; Coming Soon may be outdated')
    d, _ = line_data(html, 'D')
    lu, _ = line_data(html, 'LU')
    d = copy.deepcopy(d)
    lu = copy.deepcopy(lu)
    homes = d['h']
    communities = d['c']
    old_count = len(homes)
    response = fetch(session, SOURCE)
    try:
        items, table_count = parse_inventory(response.text)
    except RuntimeError as exc:
        if 'Only 0 listings parsed' not in str(exc):
            raise
        print('Standard page contains no inventory tables; checking printable report', flush=True)
        response = fetch(session, PRINT_SOURCE)
        items, table_count = parse_inventory(response.text)
    if len(items) < max(50, (old_count - sum(h['s'] in ('S','C') for h in homes)) / 2):
        raise RuntimeError('Inventory is less than half the existing available-home count')
    by_lot = {lot_key(h.get('lot')): h for h in homes if lot_key(h.get('lot'))}
    by_addr = {address_key(h.get('a')): h for h in homes if h.get('a')}
    by_community = {c['id']: c for c in communities}
    added = changed = removed = retained = 0
    seen = set()
    for item in items:
        key = item['lot']
        home = by_lot.get(key) or by_addr.get(address_key(item['a']))
        if home is not None and (lot_key(home.get('lot')) not in ('', key) and address_key(home.get('a')) != address_key(item['a'])):
            raise RuntimeError(f'Lot/address mismatch: {item["a"]}')
        if home is not None:
            community_id = home['cm']
        else:
            # Match community name (without collection) and city, never silently merge different cities.
            base_name = re.split(r'\s*[-–—]\s*', item['collection'], maxsplit=1)[0].strip()
            matches = [c for c in communities if norm(c['n']) == norm(base_name) and norm(c['c']) == norm(item['city'])]
            if len(matches) > 1:
                raise RuntimeError(f'Ambiguous community: {base_name}, {item["city"]}')
            if matches:
                community = matches[0]
            else:
                stem = re.sub(r'[^a-z0-9]+', '-', base_name.casefold()).strip('-')
                cid = stem
                n = 2
                while cid in by_community:
                    cid = f'{stem}-{n}'
                    n += 1
                community = dict(id=cid, n=base_name, c=item['city'], url=BASE, hoa=None, tax=None)
                communities.append(community)
                by_community[cid] = community
            community_id = community['id']
        if key in seen:
            raise RuntimeError(f'Duplicate lot {key}')
        seen.add(key)
        if home is None:
            # Never invent links: a new home requires a verified direct homesite URL.
            if not item['path']:
                raise RuntimeError(f'New listing {item["a"]} lacks a verified homesite link; no changes published')
            home = dict(a=item['a'], s=item['s'], p=item['p'], w=item['w'], bd=item['bd'], ba=item['ba'],
                        sq=item['sq'], g=0, pl=item['pl'], cm=community_id, lot=key, miss=0)
            sibling = next((h for h in homes if h['cm'] == community_id and norm(h.get('pl')) == norm(item['pl'])), None)
            if sibling:
                home['g'] = sibling.get('g', 0)
            collection = collection_slug(item['path'])
            fee_sibling = next((h for h in homes if h['cm'] == community_id and collection_slug(lu.get(lot_key(h.get('lot')), '')) == collection), None)
            if fee_sibling:
                for field in ('hoa', 'tax'):
                    if field in fee_sibling:
                        home[field] = fee_sibling[field]
            homes.append(home)
            added += 1
        else:
            old = {k: home.get(k) for k in ('p','w','s','bd','ba','sq','pl','miss')}
            home.update({k:item[k] for k in ('p','w','s','bd','ba','sq','pl')})
            home['miss'] = 0
            if any(home.get(k) != v for k,v in old.items()):
                changed += 1
        if item['path']:
            lu[key] = item['path']
        elif key not in lu:
            raise RuntimeError(f'Missing LU link for {key}; no changes published')
    to_remove = []
    unverified_coming = []
    for home in list(homes):
        key = lot_key(home.get('lot'))
        if key in seen:
            continue
        if home.get('s') in ('S','C'):
            # A static HTTP request cannot prove View More has been fully expanded.
            # Preserve Coming Soon unless a separate browser-based verification is supplied.
            unverified_coming.append(key)
            retained += 1
            continue
        path = lu.get(key)
        if path:
            gone, reason = page_indicates_sold(session, path, key)
            if gone is True:
                to_remove.append((home, reason))
            elif gone is None:
                home['miss'] = int(home.get('miss', 0)) + 1
                if home['miss'] >= 2:
                    to_remove.append((home, 'two failed checks'))
                else:
                    retained += 1
            else:
                retained += 1
        else:
            home['miss'] = int(home.get('miss', 0)) + 1
            if home['miss'] >= 2:
                to_remove.append((home, 'two missing-link checks'))
            else:
                retained += 1
    if len(to_remove) > 15:
        raise RuntimeError(f'Would remove {len(to_remove)} homes (limit 15); no changes published')
    if to_remove and not allow_deletions:
        warnings.append(f'{len(to_remove)} removals proposed; publish blocked pending explicit --allow-deletions')
        raise RuntimeError('; '.join(warnings))
    for home, reason in to_remove:
        homes.remove(home)
        lu.pop(lot_key(home.get('lot')), None)
        removed += 1
    active = {h['cm'] for h in homes}
    d['c'] = [c for c in communities if c['id'] in active]
    # Structural checks
    if any(h['cm'] not in active for h in homes):
        raise RuntimeError('Orphaned community id')
    for k, v in lu.items():
        if str(v).rstrip('/').split('/')[-1].casefold() != str(k).casefold():
            raise RuntimeError(f'LU link mismatch: {k}')
    if len({lot_key(h.get('lot')) for h in homes}) != len(homes):
        raise RuntimeError('Duplicate lot ids in resulting homes')
    html = replace_data(html, 'D', d)
    html = replace_data(html, 'LU', lu)
    eastern = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))
    try:
        from zoneinfo import ZoneInfo
        eastern = dt.datetime.now(ZoneInfo('America/New_York'))
    except ImportError:
        pass
    html = replace_data(html, 'UPDATED', eastern.strftime('%B %-d, %Y'))
    # Confirm all photo arrays and constants were preserved exactly from selected base.
    base_for_lock = laptop if laptop_used else before
    for name in LOCKED:
        _, span_a = line_data(base_for_lock, name)
        _, span_b = line_data(html, name)
        if base_for_lock[span_a[0]:span_a[1]] != html[span_b[0]:span_b[1]]:
            raise RuntimeError(f'Locked {name} changed unexpectedly')
    stats = dict(source=SOURCE, source_tables=table_count, source_listings=len(items),
                 homes=len(homes), coming_soon=sum(h['s'] in ('S','C') for h in homes),
                 communities=len(d['c']), added=added, changed=changed, removed=removed,
                 missing_retained=retained, coming_soon_unverified=len(unverified_coming),
                 laptop_sync=laptop_used, warnings=warnings)
    return html, stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true', help='Write updated index.html after all checks')
    parser.add_argument('--allow-deletions', action='store_true', help='Allow <=15 individually validated removals')
    parser.add_argument('--laptop', type=pathlib.Path, help='Optional newer laptop HTML snapshot')
    args = parser.parse_args()
    html = PAGE.read_text(encoding='utf-8')
    laptop = args.laptop.read_text(encoding='utf-8') if args.laptop else None
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT
    updated, stats = sync(html, laptop, session, allow_deletions=args.allow_deletions)
    print(json.dumps(stats, indent=2))
    if args.publish:
        PAGE.write_text(updated, encoding='utf-8')
        print('PUBLISHED: index.html updated')
    else:
        print('DRY RUN: index.html unchanged')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'INVENTORY REFRESH FAILED: {exc}', file=sys.stderr)
        sys.exit(1)
