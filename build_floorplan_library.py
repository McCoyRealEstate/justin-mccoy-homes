"""Read-only media enrichment; never changes source inventory."""
import json,sys,hashlib,concurrent.futures,time
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
  if (site.get('sqft'),site.get('beds'),site.get('baths',0)+.5*site.get('halfBaths',0))!=(h['sq'],h['bd'],h['ba']):raise ValueError('spec mismatch')
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
  if len(floors)!=site.get('stories') or not floors or not plan.get('number'):raise ValueError('floor count or model')
  tour=site.get('virtualTourUrl') or plan.get('virtualTourUrl')
  if not isinstance(tour,str) or urlparse(tour).scheme!='https' or urlparse(tour).hostname!='hd.lennar.com':tour=None
  model={'code':plan['number'],'garage':garage,'sqft':h['sq'],'beds':h['bd'],'baths':h['ba'],'floors':floors}
  return lot,model,tour,None
 except Exception as e:return lot,None,None,str(e)[:140]
library={};lots={};errors={}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for lot,model,tour,error in pool.map(extract,feed['D']['h']):
  if error:errors[lot]=error;continue
  key=hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()
  library[key]=model;lots[lot]={'model':key,'tour':tour}
out={'models':library,'lots':lots}
(root/'data/floorplans.json').write_text(json.dumps(out,separators=(',',':')))
print(json.dumps({'verified':len(lots),'unique_configurations':len(library),'unverified':errors}))
