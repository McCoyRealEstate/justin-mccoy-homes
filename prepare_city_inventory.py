#!/usr/bin/env python3
"""Build a city-page input snapshot from the *verified* homepage candidate.
Fail closed if community names/cities cannot be grounded.
"""
import json,re,sys,datetime
from pathlib import Path
from urllib.parse import urlparse
source=Path(sys.argv[1] if len(sys.argv)>1 else 'index.html')
html=source.read_text(encoding='utf-8')
m=re.search(r'(?m)^const\s+D\s*=\s*',html)
if not m:raise SystemExit('Missing inventory data constant')
data=json.JSONDecoder().raw_decode(html[m.end():])[0]
communities=data['c'];homes=data['h']
if len(homes)<100 or len(communities)<20:raise SystemExit('Unusually small verified inventory')
reference=json.loads(Path('data/inventory.json').read_text())
known={}
for item in reference['listings']:
    known.setdefault(item['community'].lower(),item['city'])
def val(obj,*keys):
    for k in keys:
        v=obj.get(k)
        if isinstance(v,str) and v.strip():return v.strip()
    return ''
out=[]
unmatched=[]
for c in communities:
    label=val(c,'name','n','community','title')
    city=val(c,'city','ct','locationCity')
    if not city and label:city=known.get(label.lower(),'')
    if not city and label:
        matches={v for k,v in known.items() if k.split(' - ')[0]==label.lower().split(' - ')[0]}
        if len(matches)==1:city=matches.pop()
    if not city:
        parts=urlparse(c.get('url','')).path.strip('/').split('/')
        if len(parts)>=5 and parts[:3]==['new-homes','florida','orlando']:city=parts[3].replace('-',' ').title().replace('St Cloud','St. Cloud')
    if not label or not city:
        unmatched.append({'id':c.get('id'),'label':label,'keys':list(c.keys())[:12]})
        continue
    out.append({'id':c['id'],'community':label,'city':city,'url':c.get('url','')})
if unmatched:print('Unmapped communities (not published):',json.dumps(unmatched[:10]))
if len(out)<15:raise SystemExit('Insufficient grounded city/community mappings')
ids={c['id']:c for c in out}
counts={i:0 for i in ids}
for h in homes:
    if h.get('cm') in counts and h.get('s') not in ('S','C'):counts[h['cm']]+=1
listings=[{'community':c['community'],'city':c['city'],'verified_home_count':counts[c['id']]} for c in out if counts[c['id']]>0]
if not listings:raise SystemExit('No verified community listings')
# Separate verified home details for community presentation. Preserve the original
# community-level listings schema used by city SEO pages.
def const(k):
    m=re.search(r'(?m)^const\s+'+k+r'\s*=\s*',html)
    return json.JSONDecoder().raw_decode(html[m.end():])[0]
PH,HIMG,PLANPH,IMG=[const(k) for k in ('PH','HIMG','PLANPH','IMG')]
def image(v):
    if type(v) is int:v=PH[v] if 0<=v<len(PH) else None
    return v if isinstance(v,str) and v.startswith(('data:image/','https://cdn.lennar.com/','https://lennar.bynder.com/','https://www.lennar.com/')) else ''
for c in out:
    c['monument_photo']=image(IMG.get(c['id']))
def photo(h):
    lot=str(h['lot'])
    for k in (lot,lot.lower(),lot.upper()):
        if image(HIMG.get(k)):return image(HIMG[k]),'Listing photo'
    p=image(PLANPH.get(h['cm']+'|'+str(h.get('pl','')).strip().lower()))
    if p:return p,'Same floor plan in this community'
    return image(IMG.get(h['cm'])),'Community monument'
home_listings=[]
for h in homes:
    c=ids.get(h.get('cm'))
    if not c:continue
    status=h.get('s')
    is_soon=status in ('S','C') or h.get('np')==1
    price=h.get('p')
    photo_url,photo_label=photo(h)
    assert photo_url, 'Missing photo for '+str(h['lot'])
    home_listings.append({
        'photo':photo_url,'photo_label':photo_label,
        'community':c['community'],'city':c['city'],'community_id':c['id'],
        'lot':h.get('lot',''),'address':h.get('a',''),
        'plan':h.get('pl',''),'beds':h.get('bd'),
        'baths':h.get('ba'),'sqft':h.get('sq'),
        'price':price if not is_soon and isinstance(price,(int,float)) and price>0 else None,
        'availability':('Coming soon' if is_soon else 'Move-in ready' if status=='M' else 'Under construction' if status=='U' else 'Confirm availability')
    })
if len(home_listings)<100:raise SystemExit('Verified community home export unexpectedly small')
payload={'source':'verified homepage inventory','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified_count':len(homes),'community_count':len(out),'communities':out,'listings':listings,'homes':home_listings}
target=Path(sys.argv[2] if len(sys.argv)>2 else 'lennar_preview/city-inventory.json')
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(payload,indent=2))
print('Prepared',len(listings),'communities for city pages from',len(homes),'verified homes')
