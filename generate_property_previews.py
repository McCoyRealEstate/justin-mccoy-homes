"""Generate share landing pages from the verified deployment feed."""
import json, re, html
from pathlib import Path
from urllib.parse import quote
import sys
p=Path(sys.argv[1])
f=json.loads((p/'data/verified-homepage.json').read_text())
out=p/'homes';out.mkdir(exist_ok=True)
communities={c['id']:c for c in f['D']['c']}
def image(v):
    if isinstance(v,int) and not isinstance(v,bool):
        v=f['PH'][v] if 0<=v<len(f['PH']) else None
    if isinstance(v,str) and v.startswith('/assets/inventory/') and (p/v.lstrip('/')).is_file():return 'https://jus3d.com'+v
    if isinstance(v,str) and v.startswith('https://cdn.lennar.com/'):return v
    return None
e=lambda v:html.escape(str(v),quote=True)
count=0
for h in f['D']['h']:
    lot=str(h.get('lot',''))
    if not re.fullmatch(r'[A-Za-z0-9_-]+',lot):continue
    c=communities.get(h['cm'],{})
    name=c.get('n') or c.get('name') or ''
    plan=h.get('pl') or 'New home'
    address=h.get('a') or ''
    price='Contact for pricing' if h.get('s') in ('S','C') or h.get('np')==1 or not h.get('p') else '$'+format(int(h['p']),',')
    title=f'{plan} | {name} | {price}'
    desc=f"{address} · {h.get('bd',0)} beds · {h.get('ba',0)} baths · {h.get('sq',0):,} sq ft. Contact Justin McCoy for current availability."
    photo=next((v for v in (image(f['HIMG'].get(k)) for k in (lot,lot.lower(),lot.upper())) if v),None)
    photo=photo or image(f['PLANPH'].get(h['cm']+'|'+plan.lower())) or 'https://jus3d.com/og-justin-mccoy-v2.png'
    url='https://jus3d.com/homes/'+lot+'.html'
    target='/?home='+quote(lot)
    tags={'og:title':title,'og:description':desc,'og:image':photo,'og:url':url,'og:type':'website'}
    meta=''.join(f'<meta property="{k}" content="{e(v)}">' for k,v in tags.items())
    (out/(lot+'.html')).write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,follow"><title>{e(title)}</title><meta name="description" content="{e(desc)}">{meta}<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{e(photo)}"></head><body style="font:16px system-ui;color:#102d49;max-width:650px;margin:40px auto;padding:20px"><h1>{e(title)}</h1><p>{e(desc)}</p><a href="{e(target)}">View current property details</a><script>location.replace({json.dumps(target)}+(new URLSearchParams(location.search).get("lang")?"&lang="+encodeURIComponent(new URLSearchParams(location.search).get("lang")):""))</script></body></html>',encoding='utf-8')
    count+=1
assert count==len(f['D']['h']), 'Missing or invalid property IDs'
assert len(list(out.glob('*.html')))==count, 'Duplicate property IDs'
print('Generated property share previews:',count)
