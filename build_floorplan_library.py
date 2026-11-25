"""Read-only media enrichment; never changes source inventory."""
import json,sys,hashlib,concurrent.futures,time,os
from pathlib import Path
from urllib.parse import urlparse,urljoin
import requests
from bs4 import BeautifulSoup
root=Path(sys.argv[1])
feed=json.loads((root/'data/verified-homepage.json').read_text())
base='https://www.lennar.com/new-homes/florida/orlando/'
def read(url):
 for attempt in range(3):
  r=requests.get(url,timeout=18,headers={'User-Agent':'Mozilla/5.0 Chrome/131.0.0.0 Safari/537.36'})
  if r.status_code not in (429,502,503,504) or attempt==2:break
  delay=r.headers.get('Retry-After','')
  time.sleep(min(60,max(2,int(delay))) if delay.isdigit() else 5*(2**attempt))
 r.raise_for_status()
 if urlparse(r.url).path.rstrip('/').lower()!=urlparse(url).path.rstrip('/').lower():raise ValueError('redirect')
 return json.loads(BeautifulSoup(r.text,'html.parser').find('script',id='__NEXT_DATA__').string)['props']['pageProps']['initialApolloState']
def canon(u):return urlparse(urljoin(base,u or '')).path.rstrip('/').lower()
def one(matches):
 if len(matches)!=1:raise ValueError('ambiguous identity')
 return matches[0]
def extract(h):
 lot=str(h['lot']).lower()
 try:
  url=urljoin(base,feed['LU'][lot])
  if urlparse(url).hostname!='www.lennar.com' or not canon(url).endswith('/'+lot):raise ValueError('lot URL')
  st=read(url)
  site=one([v for v in st.values() if isinstance(v,dict) and v.get('__typename')=='HomesiteType' and str(v.get('lotid','')).lower()==lot and canon(v.get('url'))==canon(url)])
  plan=st[site['plan']['__ref']]
  if canon(plan.get('url'))!=canon(url).rsplit('/',1)[0] or canon(plan.get('url')).rsplit('/',1)[0]!=h['collection_url']:raise ValueError('collection mismatch')
  raw_baths=site.get('baths',0)
  # Fractional totals already include the half bath.
  total_baths=raw_baths if raw_baths%1 else raw_baths+.5*site.get('halfBaths',0)
  source_specs=(site.get('sqft'),site.get('beds'),total_baths)
  inventory_specs=(h['sq'],h['bd'],h['ba'])
  if source_specs!=inventory_specs:raise ValueError(f'spec mismatch: source={source_specs}, inventory={inventory_specs}, raw baths={site.get("baths")}, half={site.get("halfBaths")}')
  garage=site.get('garages')
  if type(garage)!=int or not 0<=garage<=6:raise ValueError('unknown garage')
  floors=[]
  for f in plan.get('floorplans',[]):
   variants={}
   for k in ('default','reversed'):
    u=(f.get(k) or {}).get('image',{}).get('url','')
    if urlparse(u).scheme=='https' and urlparse(u).hostname=='cdn.lennar.com' and urlparse(u).path.lower().endswith(('.svg','.png','.jpg','.webp','.jpeg')):variants[k]=u
   if 'default' not in variants:raise ValueError('missing drawing')
   floors.append({'name':f['name'],'variants':variants})
  if len(floors)!=site.get('stories') or not floors or not plan.get('number'):raise ValueError(f'floor count or model: drawings={len(floors)}, stories={site.get("stories")}, code={plan.get("number")}')
  tour=site.get('virtualTourUrl') or plan.get('virtualTourUrl')
  if not isinstance(tour,str) or urlparse(tour).scheme!='https' or urlparse(tour).hostname!='hd.lennar.com':tour=None
  model={'code':plan['number'],'garage':garage,'sqft':h['sq'],'beds':h['bd'],'baths':h['ba'],'floors':floors}
  return lot,model,tour,None
 except Exception as e:return lot,None,None,str(e)[:140]
# Cache only exact homesite identities; never infer media from a plan name.
cache_path=Path(os.environ.get('MEDIA_CACHE_PATH',str(root/'data'/'media-cache.json')))
try: cache=json.loads(cache_path.read_text())
except (OSError,ValueError): cache={}
if not isinstance(cache,dict):cache={}
now=time.time()
def identity(h):
 lot=str(h['lot']).lower()
 return json.dumps([lot,feed['LU'].get(lot),h.get('collection_url'),h.get('sq'),h.get('bd'),h.get('ba'),h.get('plan'),h.get('garages'),h.get('features')],sort_keys=True)
identities={str(h['lot']).lower():identity(h) for h in feed['D']['h']}
def cached_extract(h):
 lot=str(h['lot']).lower()
 old=cache.get(identities[lot],{})
 age=now-old.get('verified_at',0)
 if old.get('model') and old.get('tour') and 0<=age<86400:
  return lot,old['model'],old['tour'],None,'cache'
 lot,model,tour,error=extract(h)
 # Only transient upstream failures may reuse recently verified media.
 if error and old.get('model') and 0<=age<604800 and any(x in error.lower() for x in ('429','502','503','504','timeout','timed out','connection')):
  return lot,old['model'],old.get('tour'),None,'fallback'
 return lot,model,tour,error,'fresh'
library={};lots={};errors={};next_cache={};counts={'cache':0,'fallback':0,'fresh':0}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for lot,model,tour,error,origin in pool.map(cached_extract,feed['D']['h']):
  if error:errors[lot]=error;continue
  counts[origin]+=1
  ident=identities[lot]
  next_cache[ident]={'model':model,'tour':tour,'verified_at':now} if origin=='fresh' else cache[ident]
  key=hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()
  library[key]=model;lots[lot]={'model':key,'tour':tour}
cache_path.parent.mkdir(parents=True,exist_ok=True)
cache_path.write_text(json.dumps(next_cache,separators=(',',':')))
out={'models':library,'lots':lots}
tour_index={}
for lot,entry in lots.items():
 if entry.get('tour'):
  item=tour_index.setdefault(entry['tour'],{'url':entry['tour'],'homesites':[],'models':[]})
  item['homesites'].append(lot)
  code=library[entry['model']]['code']
  if code not in item['models']:item['models'].append(code)
(root/'data/virtual-tours.json').write_text(json.dumps({'unique_tours':len(tour_index),'tours':list(tour_index.values())},indent=2))
print('Unique virtual tour URLs:',len(tour_index))
(root/'data/floorplans.json').write_text(json.dumps(out,separators=(',',':')))
print(json.dumps({'verified':len(lots),'unique_configurations':len(library),'unverified':errors,'cache_counts':counts}))
