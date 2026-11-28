#!/usr/bin/env python3
"""Build conservative city discovery pages from the repository's inventory snapshot.
Never edits the homepage or claims live prices/availability.
"""
import json,re,sys
from pathlib import Path
from html import escape
from urllib.parse import quote
ROOT=Path(__file__).resolve().parent
data=json.loads(Path(sys.argv[1]).read_text() if len(sys.argv)>1 else (ROOT/'data/inventory.json').read_text())
cities={'Groveland':'Groveland','Clermont':'Clermont','Minneola':'Minneola','Saint Cloud':'St. Cloud','Davenport':'Davenport','Haines City':'Haines City','Kissimmee':'Kissimmee','Eustis':'Eustis'}
def slug(s):return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
def esc(s):return escape(str(s),quote=True)
def page(title,desc,canonical,body):
    schema={"@context":"https://schema.org","@type":"WebPage","@id":canonical+"#webpage","name":title,"url":canonical,"description":desc,"isPartOf":{"@type":"WebSite","@id":"https://jus3d.com/#website","name":"Justin McCoy | New Home Consultant","url":"https://jus3d.com/"},"publisher":{"@type":"Person","@id":"https://jus3d.com/#justin-mccoy","name":"Justin McCoy","jobTitle":"New Home Consultant","url":"https://jus3d.com/","worksFor":{"@type":"Organization","name":"Lennar","url":"https://www.lennar.com/"}}}
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><meta name="description" content="'+esc(desc)+'"><link rel="canonical" href="'+esc(canonical)+'"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:type" content="website"><meta property="og:title" content="'+esc(title)+'"><meta property="og:description" content="'+esc(desc)+'"><meta property="og:url" content="'+esc(canonical)+'"><meta property="og:image" content="https://jus3d.com/og-preview.png"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">'+json.dumps(schema,separators=(',',':'))+'</script><style>body{margin:0;font:17px/1.6 system-ui,-apple-system,sans-serif;background:#f6f8fa;color:#182c3d}header{background:#142638;color:white;padding:18px max(24px,calc((100vw - 900px)/2))}header a{color:white}main{max-width:900px;margin:auto;padding:38px 24px 90px}h1{font-size:clamp(2rem,5vw,3.3rem);line-height:1.15}h2{margin-top:42px}a{color:#135b83}article{background:white;padding:20px 24px;border-radius:12px;margin:14px 0;border:1px solid #dce3e9}.button{display:inline-block;background:#142638;color:white;padding:13px 22px;border-radius:8px;text-decoration:none}footer{padding:25px;text-align:center;color:#52606a}</style><style>#jm-language{max-width:145px;min-width:0;background:#102d49;color:white;border:1px solid #bfa16b;border-radius:3px;padding:8px;font:12px system-ui}header{flex-wrap:wrap}@media(max-width:620px){#jm-language{max-width:110px;padding:6px;font-size:11px}.navin{height:auto!important;min-height:68px;flex-wrap:wrap;gap:8px;padding:10px 0}.navin .navlinks{margin-left:auto}}</style><script defer src="/assets/jm-language.js"></script><script defer src="/assets/jm-contact.js"></script></head><body><header><a class="brand" href="/">Justin <span>McCoy</span><small>NEW HOME CONSULTANT</small></a></header><main>'+body+'</main><footer>Justin McCoy · New Home Consultant, Lennar Homes — Orlando Division · <a href="/">Browse Central Florida homes</a><p>Prices, inventory, availability, incentives, financing offers, features, and estimated completion dates are subject to change at any time without notice. Restrictions may apply. Contact Justin McCoy, Lennar New Home Consultant, at <a href="tel:+14075725398">407-572-5398</a> for today’s pricing, available inventory, current incentives, and complete details.</p></footer></body></html>'
out=ROOT/'areas';out.mkdir(exist_ok=True)
links=[]
for city,display in cities.items():
    communities=sorted({r['community'] for r in data['listings'] if r.get('city')==city})
    if not communities:continue
    name=slug(display);url='https://jus3d.com/areas/'+name+'.html'
    title='Lennar New Homes in '+display+', FL | Justin McCoy'
    desc='Explore Lennar new construction homes and communities in '+display+', Florida. Browse available homes and connect with Justin McCoy, New Home Consultant.'
    cards=''.join('<article><h3>'+esc(c)+'</h3><a href="/">View Homes</a></article>' for c in communities)
    body='<p><a href="/areas/">Central Florida communities</a> / '+esc(display)+'</p><h1>New Construction Homes in '+esc(display)+', Florida</h1><p>Lennar communities, available homes and pricing in '+esc(display)+'.</p><a class="button" href="/">Browse available homes</a><h2>Lennar communities in '+esc(display)+'</h2>'+cards+'<h2>Private Tours &amp; Inquiries</h2><p><a href="mailto:Justin.McCoy@Lennar.com">Email Justin McCoy</a> · <a href="tel:+14075725398">407-572-5398</a></p>'
    (out/(name+'.html')).write_text(page(title,desc,url,body),encoding='utf-8')
    links.append((display,name,url))
indexurl='https://jus3d.com/areas/'
body='<h1>Central Florida New Construction</h1><a class="button" href="/">Search all homes</a><h2>Explore by city</h2>'+''.join('<article><h3><a href="/areas/'+slug+'.html">'+esc(display)+', FL</a></h3></article>' for display,slug,_ in links)
(out/'index.html').write_text(page('Central Florida New Construction Communities | Justin McCoy | Lennar Orlando','Explore new construction communities by city in Central Florida with Justin McCoy.',indexurl,body),encoding='utf-8')
urls=['https://jus3d.com/',indexurl]+[x[2] for x in links]
(ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('  <url><loc>'+esc(u)+'</loc></url>\n' for u in urls)+'</urlset>\n',encoding='utf-8')
print('Generated',len(links),'city pages and sitemap')
