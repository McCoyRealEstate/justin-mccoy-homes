#!/usr/bin/env python3
"""Create priority community landing pages from the same verified city inventory.
Run AFTER generate_local_pages.py. No prices or availability claims.
"""
import json,sys
from pathlib import Path
from html import escape
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parent
data=json.loads(Path(sys.argv[1]).read_text() if len(sys.argv)>1 else (ROOT/'data/inventory.json').read_text())
targets=[
 ('Meadow Pointe','Groveland','meadow-pointe'),
 ('Hidden Ridge','Groveland','hidden-ridge'),
 ('Sugarloaf Ridge','Minneola','sugarloaf-ridge'),
 ('Waterlin','St. Cloud','waterlin'),
 ('Waterstone','Groveland','waterstone'),
]
def esc(s):return escape(str(s),quote=True)
def cityslug(city):return {'St. Cloud':'st-cloud'}.get(city,city.lower().replace(' ','-'))
def render(title,desc,url,body):
    schema={'@context':'https://schema.org','@type':'WebPage','name':title,'url':url,'description':desc,'isPartOf':{'@type':'WebSite','name':'McCoy Real Estate','url':'https://jus3d.com/'}}
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><meta name="description" content="'+esc(desc)+'"><link rel="canonical" href="'+url+'"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><meta property="og:type" content="website"><meta property="og:title" content="'+esc(title)+'"><meta property="og:description" content="'+esc(desc)+'"><meta property="og:url" content="'+url+'"><meta property="og:image" content="https://jus3d.com/og-preview.png"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">'+json.dumps(schema,separators=(',',':'))+'</script><style>body{margin:0;font:17px/1.6 system-ui,-apple-system,sans-serif;background:#f6f8fa;color:#182c3d}header{background:#142638;color:white;padding:18px max(24px,calc((100vw - 900px)/2))}header a{color:white}main{max-width:900px;margin:auto;padding:38px 24px 90px}h1{font-size:clamp(2rem,5vw,3.3rem);line-height:1.15}h2{margin-top:42px}a{color:#135b83}article{background:white;padding:20px 24px;border-radius:12px;margin:14px 0;border:1px solid #dce3e9}.button{display:inline-block;background:#142638;color:white;padding:13px 22px;border-radius:8px;text-decoration:none}footer{padding:25px;text-align:center;color:#52606a}</style></head><body><header><a href="/">McCoy Real Estate · Jus3D.com</a></header><main>'+body+'</main><footer>Justin McCoy · New Home Consultant, Lennar Homes Orlando Division</footer></body></html>'
out=ROOT/'communities';out.mkdir(exist_ok=True)
links=[]
for name,city,slug in targets:
    rows=sorted({str(r['community']) for r in data['listings'] if str(r.get('community','')).lower().split(' - ')[0]==name.lower()})
    if not rows:raise SystemExit('No verified inventory for '+name)
    url='https://jus3d.com/communities/'+slug+'.html'
    title=name+' New Construction Homes | '+city+', FL'
    desc='Explore Lennar '+name+' in '+city+', Florida with Justin McCoy. See community collections and browse current home inventory on Jus3D.com.'
    cards=''.join('<article><h3>'+esc(c)+'</h3><p>View the latest displayed homes and floor plans using the main inventory search. Specific homes and pricing can change.</p></article>' for c in rows)
    body='<p><a href="/communities/">Communities</a> / '+esc(name)+'</p><h1>'+esc(name)+' New Construction Homes in '+esc(city)+', Florida</h1><p>Considering a Lennar home at '+esc(name)+'? Justin McCoy can help you compare the community collections, floor plans, move-in timelines and currently displayed inventory.</p><a class="button" href="/">Browse current home inventory</a><h2>Explore '+esc(name)+' collections</h2>'+cards+'<h2>Plan your visit</h2><p>Inventory, pricing, incentives and completion dates can change. Contact Justin to confirm current details and arrange a tour before making plans.</p><p><a href="/areas/'+cityslug(city)+'.html">Explore more homes in '+esc(city)+'</a> · <a href="mailto:Justin.McCoy@Lennar.com">Email Justin</a> · <a href="tel:+16893216555">689-321-6555</a></p>'
    (out/(slug+'.html')).write_text(render(title,desc,url,body),encoding='utf-8')
    links.append((name,city,slug,url))
hub='https://jus3d.com/communities/'
body='<h1>Featured Lennar New Construction Communities</h1><p>Explore community-specific information with Justin McCoy, then browse current Central Florida inventory.</p>'+''.join('<article><h2><a href="/communities/'+slug+'.html">'+esc(name)+'</a></h2><p>'+esc(city)+', Florida</p></article>' for name,city,slug,_ in links)+'<p><a href="/areas/">Browse by city</a> · <a href="/">Search all homes</a></p>'
(out/'index.html').write_text(render('Featured Lennar Communities in Central Florida | McCoy Real Estate','Explore Meadow Pointe, Hidden Ridge, Sugarloaf Ridge, Waterlin and Waterstone with Justin McCoy.',hub,body),encoding='utf-8')
for name,city,slug,_ in links:
    path=ROOT/'areas'/(cityslug(city)+'.html')
    if not path.exists():raise SystemExit('Missing city page '+str(path))
    html=path.read_text()
    needle='<h3>'+esc(name)
    # A city page may list a collection suffix; insert a direct community link ahead of the first matching collection.
    i=html.find(needle)
    if i>=0:
        html=html[:i]+'<p><a href="/communities/'+slug+'.html">Explore '+esc(name)+' community guide</a></p>'+html[i:]
        path.write_text(html)
sitemap=ROOT/'sitemap.xml'
tree=ET.parse(sitemap)
ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
existing={n.text for n in tree.getroot().iter(ns+'loc')}
for url in [hub]+[x[3] for x in links]:
    if url not in existing:
        entry=ET.SubElement(tree.getroot(),ns+'url')
        ET.SubElement(entry,ns+'loc').text=url
ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
tree.write(sitemap,encoding='utf-8',xml_declaration=True)
print('Generated',len(links),'community guides and updated sitemap')
