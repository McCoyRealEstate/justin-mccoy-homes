import json,re,requests,hashlib
from bs4 import BeautifulSoup
from urllib.parse import urlparse
BASE='https://www.lennar.com'
paths=["/new-homes/florida/orlando/groveland/hidden-ridge/estate-collection/mccartney","/new-homes/florida/orlando/groveland/meadow-pointe/classic-collection/mccartney","/new-homes/florida/orlando/davenport/reedy-isle/classic-collection/mccartney","/new-homes/florida/orlando/davenport/providence/classic-collection/mccartney","/new-homes/florida/orlando/haines-city/crosswinds/classic-collection/mccartney","/new-homes/florida/orlando/haines-city/groves-at-grenelefe/classic-collection/mccartney"]
s=requests.Session()
s.headers['User-Agent']='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36'
for path in paths:
 try:
  r=s.get(BASE+path,timeout=45);r.raise_for_status()
  if urlparse(r.url).path.rstrip('/').lower()!=path.lower():raise ValueError('Redirect mismatch')
  soup=BeautifulSoup(r.text,'html.parser')
  data=json.loads(soup.find('script',id='__NEXT_DATA__').string)
  st=data['props']['pageProps']['initialApolloState']
  print(json.dumps({'source':path,'types':sorted(set(v.get('__typename','') for v in st.values() if isinstance(v,dict))) }))
  for key,obj in st.items():
   if not isinstance(obj,dict):continue
   if obj.get('__typename')=='PlanType' and obj.get('url','').rstrip('/').lower()==path.lower():
    for f in obj.get('floorplans',[]):
     for variant in ('default','reversed'):
      u=(f.get(variant) or {}).get('image',{}).get('url')
      if u and urlparse(u).hostname=='cdn.lennar.com':
       im=s.get(u,timeout=30);im.raise_for_status()
       print(json.dumps({'comparison':path,'garage':obj.get('garages'),'number':obj.get('number'),'floor':f.get('name'),'variant':variant,'image':u,'sha256':hashlib.sha256(im.content).hexdigest(),'bytes':len(im.content)}))
   fields={k:v for k,v in obj.items() if re.search(r'floor.?plan|garage|carport|planNumber|interactive|matterport|virtualTour',k,re.I)}
   if fields:print(json.dumps({'source':path,'object':key,'fields':fields},default=str)[:18000])
   if obj.get('__typename') in ('PlanType','HomesiteType') and (obj.get('name','').lower() in ('mccartney','crestone') or str(obj.get('lotid','')).lower()==path.split('/')[-1]):
    print(json.dumps({'source':path,'object':key,'keys':list(obj),'identity':{k:obj.get(k) for k in ('name','number','beds','baths','halfBaths','sqft','stories','url','community','plan','lotid')}}))
  for img in soup.find_all('img'):
   if re.search(r'floor.?plan|first floor|second floor',str(img),re.I):print(str(img)[:2000])
 except Exception as e:print(json.dumps({'source':path,'error':str(e)}))
