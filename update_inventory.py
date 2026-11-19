#!/usr/bin/env python3
"""Refresh public inventory from Lennar's Orlando printable report.
Requires: pip install requests beautifulsoup4
Runs in GitHub Actions; failure leaves the last verified snapshot untouched.
"""
import re, json, datetime, pathlib, sys
import requests
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).parent
PAGE=ROOT/'index.html'
URL='https://www.lennar.com/new-homes/florida/orlando/promo/olhlen_nhc_inventory?print=true'
s=requests.get(URL,timeout=35,headers={'User-Agent':'Mozilla/5.0 (compatible; inventory-update/1.0)'});s.raise_for_status()
soup=BeautifulSoup(s.text,'html.parser')
text=soup.get_text('\n',strip=True)
# Parse report via individual table rows, keeping the section heading preceding each table.
items=[]; current=''; location=''
for node in soup.find_all(['h1','h2','h3','h4','p','table']):
 if node.name!='table':
  t=node.get_text(' ',strip=True)
  if ' | ' in t and re.search(r',\s*FL\s*\d{5}',t):
   current,location=t.split(' | ',1)
  continue
 headers=[x.get_text(' ',strip=True).lower() for x in node.select('tr')[:1] for x in x.find_all(['td','th'])]
 if not any('homesite' in h for h in headers):continue
 for tr in node.select('tr')[1:]:
  vals=[x.get_text(' ',strip=True) for x in tr.find_all(['td','th'])]
  if len(vals)<7:continue
  addr,lot,plan,bb,sq,avail,price=vals[:7]
  amounts=[int(x.replace(',','')) for x in re.findall(r'\$([\d,]+)',price)]
  beds=re.findall(r'\d+(?:\.\d+)?',bb)
  if not amounts or len(beds)<2:continue
  city=re.search(r',\s*([^,]+),\s*FL\s*\d{5}',location)
  items.append(dict(address=addr,lot=lot.lstrip('#'),plan=plan,beds=int(float(beds[0])),baths=float(beds[1]),sqft=int(re.sub(r'\D','',sq) or 0),availability=avail,price=amounts[0],was=amounts[-1],community=current,city=city.group(1) if city else ''))
if len(items)<50:raise RuntimeError(f'Only {len(items)} homes parsed; refusing to overwrite snapshot')
html=PAGE.read_text()
start=html.index('const D = ')+len('const D = ')
old,end=json.JSONDecoder().raw_decode(html[start:])
old_lookup={(h['a'].strip().lower(),h['cm']):h for h in old['h']}
communities=old['c']; byname={c['n'].lower():c for c in communities}
homes=[]
for item in items:
 name=item['community'].split(' - ')[0].strip()
 c=byname.get(name.lower())
 if not c:
  slug=re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')
  c={'id':slug,'n':name,'c':item['city'],'hoa':None,'tax':None,'url':'https://www.lennar.com/new-homes/florida/orlando'}
  communities.append(c);byname[name.lower()]=c
 previous=old_lookup.get((item['address'].strip().lower(),c['id']),{})
 avail=item['availability'].lower()
 status='M' if 'move-in ready' in avail else ('S' if 'coming soon' in avail else 'U')
 homes.append({'a':item['address'],'s':status,'p':item['price'],'w':item['was'],'bd':item['beds'],'ba':item['baths'],'sq':item['sqft'],'g':previous.get('g',2),'pl':item['plan'],'cm':c['id'],'lot':previous.get('lot',item['lot']),'miss':0,'avail':item['availability']})
# Keep only explicitly marked Coming Soon records from the previous snapshot; not verified by print report.
known={(h['a'].lower(),h['cm']) for h in homes}
for h in old['h']:
 if h['s']=='S' and (h['a'].lower(),h['cm']) not in known:
  h['np']=1;h['unverified']=1;homes.append(h)
new={'c':communities,'h':homes}
now=datetime.datetime.now(datetime.timezone.utc)
html=html[:start]+json.dumps(new,separators=(',',':'))+html[start+end:]
html=re.sub(r'const IMPORTED = "[^"]+";',f'const IMPORTED = "{now.strftime("%Y-%m-%dT%H:%M:%SZ")}";',html,count=1)
html=re.sub(r'const UPDATED = "[^"]+";',f'const UPDATED = "{now.strftime("%B %d, %Y")}";',html,count=1)
PAGE.write_text(html)
print(f'Updated {len(items)} verified listings and {len(communities)} communities at {now.isoformat()}')
