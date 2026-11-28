"""Reuse the deployed homepage UI for existing city SEO routes."""
import re,sys,json
from pathlib import Path
from html import escape
p=Path(sys.argv[1])
base=(p/'index.html').read_text()
cities={'groveland':'Groveland','clermont':'Clermont','minneola':'Minneola','st-cloud':'St. Cloud','davenport':'Davenport','haines-city':'Haines City','kissimmee':'Kissimmee','eustis':'Eustis'}
for slug,city in cities.items():
    file=p/'areas'/f'{slug}.html'
    if not file.exists():continue
    old=file.read_text()
    s=base
    # Preserve the existing city-specific search metadata.
    for pattern in [r'<title>.*?</title>',r'<meta name="description"[^>]*>',r'<link rel="canonical"[^>]*>',r'<meta property="og:title"[^>]*>',r'<meta property="og:description"[^>]*>',r'<meta property="og:url"[^>]*>',r'<script type="application/ld\+json">.*?</script>']:
        m=re.search(pattern,old,re.S)
        if m:s=re.sub(pattern,lambda _:m.group(),s,count=1,flags=re.S)
    s=s.replace('<h1>Find a home<br><em>you’ll love.</em></h1>','<h1>'+escape(city)+', Florida</h1>')
    s=s.replace('New construction homes across Central Florida.','New construction homes in '+escape(city)+', Florida.')
    s=s.replace('homes=data;verified=meta.verified;', 'const scope='+json.dumps(city)+';data=data.filter(h=>normalizeCity(h.city)===normalizeCity(scope));meta={...meta,directory:(meta.directory||[]).filter(c=>normalizeCity(c.city)===normalizeCity(scope))};homes=data;verified=meta.verified;')
    s=s.replace('const cities=[...new Set([...homes,...(meta.directory||[])].map(h=>h.city).filter(Boolean))].sort();','const cities=[scope];')
    s=s.replace('sel.value=selected;}','sel.value=scope;sel.disabled=true;}',1)
    s=s.replace('</head>','<style>.city-back{display:inline-block;color:#d4b477;margin-bottom:12px;font-size:14px}.hero h1{font-size:clamp(36px,7vw,72px)}</style></head>')
    s=s.replace('<div class="wrap hero-in">','<div class="wrap hero-in"><a class="city-back" href="/">← All Central Florida homes</a>',1)
    assert 'const scope='+json.dumps(city) in s and 'sel.disabled=true' in s and 'https://jus3d.com/areas/'+slug+'.html' in s
    file.write_text(s)
    print('Premium city experience:',city)
