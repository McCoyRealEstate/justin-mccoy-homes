#!/usr/bin/env python3
"""Read-only diagnostic for Lennar Orlando inventory table context.

Temporarily replace update_inventory.py with this file and manually run the
GitHub Actions workflow. It deliberately exits with code 1 after printing
samples, preventing the workflow's commit step from running. No site files
are modified. Restore a production importer after reviewing the output.
"""
import re
import sys
import requests
from bs4 import BeautifulSoup, Tag

URL = 'https://www.lennar.com/new-homes/florida/orlando/promo/olhlen_nhc_inventory?print=true'

def clean(value, limit=220):
    return re.sub(r'\s+', ' ', value or '').strip()[:limit]

def tag_label(node):
    if not isinstance(node, Tag):
        return ''
    attrs = []
    for key in ('class', 'id'):
        value = node.get(key)
        if value:
            attrs.append(f'{key}={" ".join(value) if isinstance(value, list) else value}')
    return f'<{node.name} {" ".join(attrs)}>'.strip()

def main():
    response = requests.get(URL, timeout=40, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; inventory-diagnostic/1.0)'
    })
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    print('HTTP status:', response.status_code, flush=True)
    print('Final URL:', response.url, flush=True)
    print('HTML tables:', len(tables), flush=True)
    print('Response characters:', len(response.text), flush=True)
    for i, table in enumerate(tables[:5], 1):
        print(f'\n=== TABLE {i} CONTEXT ===', flush=True)
        headers = table.find('tr')
        print('HEADER:', clean(headers.get_text(' | ', strip=True) if headers else '', 300), flush=True)
        parent = table.parent
        print('PARENT:', tag_label(parent), flush=True)
        print('GRANDPARENT:', tag_label(parent.parent if parent else None), flush=True)
        print('PREVIOUS ELEMENTS (closest first):', flush=True)
        cursor = table
        for depth in range(4):
            if cursor is None:
                break
            found = 0
            for sibling in cursor.previous_siblings:
                if not isinstance(sibling, Tag):
                    continue
                text = clean(sibling.get_text(' ', strip=True), 240)
                if text:
                    print(f'  level={depth} {tag_label(sibling)}: {text}', flush=True)
                    found += 1
                if found >= 3:
                    break
            cursor = cursor.parent
        print('NEAREST PRECEDING TEXT:', flush=True)
        count = 0
        for string in table.find_all_previous(string=True):
            if string.find_parent('table') is not None:
                continue
            value = clean(str(string), 160)
            if value:
                print(' ', value, flush=True)
                count += 1
            if count >= 8:
                break
    print('\nDIAGNOSTIC COMPLETE. No inventory files were changed.', flush=True)
    print('Stopping intentionally so the workflow does not commit.', flush=True)
    return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'DIAGNOSTIC ERROR: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
