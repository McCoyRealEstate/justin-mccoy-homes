import json,re,requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
BASE='https://www.lennar.com'
paths=['/new-homes/florida/orlando/groveland/hidden-ridge/estate-collection/mccartney','/new-homes/florida/orlando/groveland/meadow-pointe/classic-collection/mccartney','/new-homes/florida/orlando/groveland/hidden-ridge/estate-collection/mccartney/2630672h090','/new-homes/florida/orlando/haines-city/crosswinds/ascent-collection/crestone']
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
   fields={k:v for k,v in obj.items() if re.search(r'floor.?plan|garage|carport|planNumber|interactive|matterport|virtualTour',k,re.I)}
   if fields:print(json.dumps({'source':path,'object':key,'fields':fields},default=str)[:18000])
   if obj.get('__typename') in ('PlanType','HomesiteType') and (obj.get('name','').lower() in ('mccartney','crestone') or str(obj.get('lotid','')).lower()==path.split('/')[-1]):
    print(json.dumps({'source':path,'object':key,'keys':list(obj),'identity':{k:obj.get(k) for k in ('name','number','beds','baths','halfBaths','sqft','stories','url','community','plan','lotid')}}))
  for img in soup.find_all('img'):
   if re.search(r'floor.?plan|first floor|second floor',str(img),re.I):print(str(img)[:2000])
 except Exception as e:print(json.dumps({'source':path,'error':str(e)}))
