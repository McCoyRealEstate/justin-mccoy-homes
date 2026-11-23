#!/usr/bin/env python3
"""Build a city-page input snapshot from the *verified* homepage candidate.
Fail closed if community names/cities cannot be grounded.
"""
import json,re,sys,datetime
from pathlib import Path
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
    if not label or not city:
        unmatched.append({'id':c.get('id'),'label':label,'keys':list(c.keys())[:12]})
        continue
    out.append({'id':c['id'],'community':label,'city':city})
if unmatched:print('Unmapped communities (not published):',json.dumps(unmatched[:10]))
if len(out)<15:raise SystemExit('Insufficient grounded city/community mappings')
ids={c['id']:c for c in out}
counts={i:0 for i in ids}
for h in homes:
    if h.get('cm') in counts and h.get('s') not in ('S','C'):counts[h['cm']]+=1
listings=[{'community':c['community'],'city':c['city'],'verified_home_count':counts[c['id']]} for c in out if counts[c['id']]>0]
if not listings:raise SystemExit('No verified community listings')
payload={'source':'verified homepage inventory','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified_count':len(homes),'community_count':len(out),'listings':listings}
target=Path(sys.argv[2] if len(sys.argv)>2 else 'lennar_preview/city-inventory.json')
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(payload,indent=2))
print('Prepared',len(listings),'communities for city pages from',len(homes),'verified homes')
