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
    # Rebuild route-specific identity from the city metadata, including older generated pages.
    from html import unescape
    title=unescape(re.search(r'<title>(.*?)</title>',s,re.S).group(1))
    desc=unescape(re.search(r'<meta name="description" content="([^"]*)"',s).group(1))
    url='https://jus3d.com/areas/'+slug+'.html'
    schema={"@context":"https://schema.org","@type":"WebPage","@id":url+"#webpage","name":title,"description":desc,"url":url,"isPartOf":{"@type":"WebSite","@id":"https://jus3d.com/#website","url":"https://jus3d.com/"},"publisher":{"@type":"Person","@id":"https://jus3d.com/#justin-mccoy","name":"Justin McCoy","jobTitle":"New Home Consultant","url":"https://jus3d.com/","worksFor":{"@type":"Organization","name":"Lennar","url":"https://www.lennar.com/"}}}
    s=re.sub(r'<script type="application/ld\+json">.*?</script>',lambda _: '<script type="application/ld+json">'+json.dumps(schema)+'</script>',s,count=1,flags=re.S)
    s=s.replace('<h1>Find a home <em>you’ll love.</em></h1>','<h1>'+escape(city)+', Florida</h1>')
    s=s.replace('New construction homes across Central Florida.','New construction homes in '+escape(city)+', Florida.')
    s=s.replace('homes=data;verified=meta.verified;', 'const scope='+json.dumps(city)+';data=data.filter(h=>normalizeCity(h.city)===normalizeCity(scope));meta={...meta,directory:(meta.directory||[]).filter(c=>normalizeCity(c.city)===normalizeCity(scope))};homes=data;verified=meta.verified;')
    s=s.replace('const cities=[...new Set([...homes,...(meta.directory||[])].map(h=>h.city).filter(Boolean))].sort();','const cities=[scope];')
    s=s.replace('sel.value=selected;}','sel.value=scope;sel.disabled=true;}',1)
    s=s.replace('</head>','<style>.city-back{display:inline-block;color:#d4b477;margin-bottom:12px;font-size:14px}.hero h1{font-size:clamp(36px,7vw,72px)}</style></head>')
    s=s.replace('<div class="wrap hero-in">','<div class="wrap hero-in"><a class="city-back" href="/">← All Central Florida homes</a>',1)
    assert 'const scope='+json.dumps(city) in s and 'sel.disabled=true' in s and 'https://jus3d.com/areas/'+slug+'.html' in s
    # Restore crawlable community relationships after cloning the homepage.
    from bs4 import BeautifulSoup
    from urllib.parse import urlsplit
    feed=json.loads((p/'data/verified-homepage.json').read_text())
    def norm(value):
        return re.sub(r'[^a-z0-9]','',str(value).lower())
    directory=[c for c in feed['D']['c'] if norm(c.get('city',''))==norm(city)]
    links=[]
    for c in directory:
        ident=str(c.get('id',''))
        if not re.fullmatch(r'[a-zA-Z0-9_-]+',ident): continue
        if not (p/'communities'/f'{ident}.html').is_file(): continue
        # Read the verified generated page title rather than assume feed name keys.
        detail=BeautifulSoup((p/'communities'/f'{ident}.html').read_text(),'html.parser')
        heading=detail.select_one('h1')
        if not heading: continue
        name=heading.get_text(' ',strip=True)
        links.append((ident,name))
    if links:
        schema['mentions']=[{'@type':'WebPage','name':name,'url':'https://jus3d.com/communities/'+ident+'.html'} for ident,name in links]
        s=re.sub(r'<script type="application/ld\\+json">.*?</script>',lambda _: '<script type="application/ld+json">'+json.dumps(schema)+'</script>',s,count=1,flags=re.S)
        # Use the existing footer area and native link styling; no new hero or controls.
        section='<section class="wrap" aria-label="Lennar communities in '+escape(city)+'"><h2>Lennar communities in '+escape(city)+'</h2><p>Explore community details, floor plans and current availability.</p><p>'+ ' · '.join('<a href="/communities/'+ident+'.html">'+escape(name)+'</a>' for ident,name in links)+'</p></section>'
        if re.search(r'<footer\\b',s,re.I):
            s=re.sub(r'<footer\\b',lambda m:section+m.group(),s,count=1,flags=re.I)
        else:
            s=s.replace('</body>',section+'</body>',1)
        assert all('/communities/'+ident+'.html' in s for ident,_ in links)
        print('Crawlable city community links:',city,len(links))
    file.write_text(s)
    print('Premium city experience:',city)
