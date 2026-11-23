#!/usr/bin/env python3
"""Create priority community landing pages from the same verified city inventory.
Run AFTER generate_local_pages.py. No unverified prices or availability claims. Keep previews in sync with generator.
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
    schema={'@context':'https://schema.org','@type':'WebPage','name':title,'url':url,'description':desc,'isPartOf':{'@type':'WebSite','name':'Justin McCoy | New Homes','url':'https://jus3d.com/'}}
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><meta name="description" content="'+esc(desc)+'"><link rel="canonical" href="'+url+'"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><meta property="og:type" content="website"><meta property="og:title" content="'+esc(title)+'"><meta property="og:description" content="'+esc(desc)+'"><meta property="og:url" content="'+url+'"><meta property="og:image" content="https://jus3d.com/og-preview.png"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">'+json.dumps(schema,separators=(',',':'))+'</script><style>:root{--navy:#071e35;--navy2:#0e2d48;--gold:#e9bd69;--ink:#15253a}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f6f7;color:var(--ink);font:16px/1.65 system-ui,-apple-system,sans-serif}a{color:inherit}header{background:var(--navy);border-bottom:2px solid var(--gold);color:#fff;padding:18px max(22px,calc((100vw - 1160px)/2));display:flex;justify-content:space-between;align-items:center;gap:15px}header a{text-decoration:none;font-weight:800;letter-spacing:.02em}header .brand span{color:var(--gold)}header nav{display:flex;gap:20px;align-items:center;font-size:14px}header nav a{font-weight:600}.navcta,.button{display:inline-block;background:linear-gradient(110deg,#f7d58e,#dba947);color:#091d30!important;padding:13px 23px;border-radius:9px;text-decoration:none;font-weight:800;box-shadow:0 5px 15px #071e3522}.button.alt{background:transparent;color:#fff!important;border:1px solid #ffffffb0}.hero{background:radial-gradient(circle at 85% 25%,#254c6d 0%,#0e2d48 40%,#071e35 100%);color:white;padding:75px max(22px,calc((100vw - 1160px)/2)) 85px;position:relative;overflow:hidden}.hero:after{content:' ';position:absolute;width:460px;height:460px;border:1px solid #e9bd693b;transform:rotate(35deg);right:-130px;top:-120px;pointer-events:none}.eyebrow{text-transform:uppercase;letter-spacing:.24em;color:var(--gold);font-size:12px;font-weight:800}.hero h1{font:normal clamp(2.7rem,6vw,5.4rem)/1.05 Georgia,serif;margin:14px 0 16px;max-width:840px}.hero h1 em{color:var(--gold);font-style:normal}.hero p{font-size:19px;max-width:660px;color:#e1e8ee}.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}.advisor{background:#09243d;color:white;border-top:1px solid #ffffff30;border-bottom:1px solid #ffffff30}.advisor-inner{max-width:1160px;margin:auto;padding:28px 22px;display:flex;align-items:center;justify-content:space-between;gap:20px}.advisor h2{font:normal 32px Georgia,serif;margin:0}.advisor h2 span{color:var(--gold)}.advisor p{margin:4px 0}.advisor a{color:white}.advisor .contact{font-weight:800;font-size:19px}.features{background:#102f49;color:#fff}.features-inner{max-width:1160px;margin:auto;display:grid;grid-template-columns:repeat(3,1fr);gap:20px;padding:22px}.features strong{color:var(--gold);display:block}.content{max-width:1160px;margin:auto;padding:65px 22px 90px}.content h2{font:normal clamp(2rem,4vw,2.8rem) Georgia,serif;margin:0 0 10px}.content .intro{color:#566577;margin-bottom:28px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:18px}article{background:white;border:1px solid #e1e5e9;border-radius:15px;padding:26px;box-shadow:0 8px 25px #15253a0d}article h3{margin:0 0 8px;font-size:20px}article p{color:#566577}.closing{background:linear-gradient(110deg,#071e35,#163b57);color:white;padding:52px 22px}.closing-inner{max-width:1160px;margin:auto;display:flex;justify-content:space-between;align-items:center;gap:25px}.closing h2{font:normal 36px Georgia,serif;margin:0 0 8px}.closing p{margin:0;color:#d7e0e7}footer{background:#06192c;color:#aebdca;padding:25px;text-align:center;font-size:13px}footer a{color:#e9bd69}.crumb{font-size:13px;color:#6a7b88}.crumb a{color:#2b607d}@media(max-width:700px){header nav{display:none}.hero{padding-top:54px;padding-bottom:60px}.advisor-inner,.closing-inner{display:block}.advisor .contact{margin-top:15px}.features-inner{grid-template-columns:1fr}.closing .actions{margin-top:22px}.button{width:100%;text-align:center}.hero h1{font-size:clamp(2.5rem,12vw,4rem)}}</style></head><body><header><a class="brand" href="/">Justin McCoy <span>| New Homes</span></a><nav><a href="/">Home</a><a href="/communities/">Communities</a><a href="/">Inventory</a><a class="navcta" href="tel:+14075725398">Schedule a Tour</a></nav></header>'+body+'<footer>Justin McCoy | New Homes · New Home Consultant · Lennar Homes – Orlando Division · <a href="tel:+14075725398">407-572-5398</a><br>Independent personal presentation; inventory, prices and incentives subject to confirmation.</footer></body></html>'
out=ROOT/'communities';out.mkdir(exist_ok=True)
links=[]
for name,city,slug in targets:
    rows=sorted({str(r['community']) for r in data['listings'] if str(r.get('community','')).lower().split(' - ')[0]==name.lower()})
    if not rows:raise SystemExit('No verified inventory for '+name)
    url='https://jus3d.com/communities/'+slug+'.html'
    title=name+' New Construction Homes | '+city+', FL'
    desc='Explore Lennar '+name+' in '+city+', Florida with Justin McCoy. See community collections and browse current home inventory on Jus3D.com.'
    cards=''.join('<article><h3>'+esc(c)+'</h3><p>Explore floor plans and homes in this collection through the current inventory search. Pricing and availability are subject to change.</p><a href="/">Explore inventory →</a></article>' for c in rows)
    body='<section class="hero"><div class="eyebrow">Lennar New Homes · '+esc(city)+', Florida</div><h1>'+esc(name)+'<br><em>New Construction Homes</em></h1><p>Explore Lennar new construction in '+esc(name)+'. Compare floor plans, move-in timelines and home options with a local New Home Consultant.</p><div class="actions"><a class="button" href="tel:+14075725398">Schedule a Tour</a><a class="button alt" href="/">View Available Homes →</a></div></section><section class="advisor"><div class="advisor-inner"><div><h2>Justin McCoy <span>| New Homes</span></h2><p>New Home Consultant · Lennar Homes – Orlando Division</p></div><div class="contact"><a href="tel:+14075725398">☎ 407-572-5398</a><p><a href="mailto:Justin.McCoy@Lennar.com">Justin.McCoy@Lennar.com</a></p></div></div></section><section class="features"><div class="features-inner"><div><strong>Explore Floor Plans</strong>Compare layouts and home designs</div><div><strong>Current Inventory</strong>Browse displayed homes and updates</div><div><strong>Personalized Guidance</strong>Connect directly with Justin</div></div></section><main class="content"><p class="crumb"><a href="/communities/">Communities</a> / '+esc(name)+'</p><h2>Explore '+esc(name)+' Collections</h2><p class="intro">Browse community collections below. Confirm home-specific details and incentives directly before making plans.</p><div class="cards">'+cards+'</div></main><section class="closing"><div class="closing-inner"><div><h2>Let’s Find Your New Home in '+esc(name)+'</h2><p>Get personalized guidance, current home information and a private tour.</p></div><div class="actions"><a class="button" href="tel:+14075725398">Schedule a Tour</a><a class="button alt" href="/">View All Inventory</a></div></div></section>'
    (out/(slug+'.html')).write_text(render(title,desc,url,body),encoding='utf-8')
    links.append((name,city,slug,url))
hub='https://jus3d.com/communities/'
body='<h1>Featured Lennar New Construction Communities</h1><p>Explore community-specific information with Justin McCoy, then browse current Central Florida inventory.</p>'+''.join('<article><h2><a href="/communities/'+slug+'.html">'+esc(name)+'</a></h2><p>'+esc(city)+', Florida</p></article>' for name,city,slug,_ in links)+'<p><a href="/areas/">Browse by city</a> · <a href="/">Search all homes</a></p>'
(out/'index.html').write_text(render('Featured Lennar Communities in Central Florida | Justin McCoy | New Homes','Explore Meadow Pointe, Hidden Ridge, Sugarloaf Ridge, Waterlin and Waterstone with Justin McCoy.',hub,body),encoding='utf-8')
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
