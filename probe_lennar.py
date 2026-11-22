#!/usr/bin/env python3
"""READ-ONLY GitHub connectivity/structured-data diagnostic. Never writes index.html."""
import json, os, re, sys, datetime
from collections import Counter
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE='https://www.lennar.com/new-homes/florida/orlando/'
INV=BASE+'promo/olhlen_nhc_inventory'
S=requests.Session();S.headers.update({'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Accept-Language':'en-US,en;q=0.9'})
report={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'read_only':True,'pages':[],'errors':[]}

def fetch(url):
    try:
        r=S.get(url,timeout=35,allow_redirects=True)
        entry={'requested':url,'final_url':r.url,'status':r.status_code,'bytes':len(r.content),'next_data':False,'homesite_objects':0,'community_objects':0,'statuses':{},'sample_fields':[]}
        report['pages'].append(entry)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        tag=soup.find('script',id='__NEXT_DATA__')
        if tag and tag.string:
            entry['next_data']=True
            data=json.loads(tag.string)
            state=data.get('props',{}).get('pageProps',{}).get('initialApolloState',{})
            if not isinstance(state,dict):state={}
            homes=[v for k,v in state.items() if 'HomesiteType' in k and isinstance(v,dict)]
            communities=[v for k,v in state.items() if 'CommunityType' in k and isinstance(v,dict)]
            entry['homesite_objects']=len(homes);entry['community_objects']=len(communities)
            entry['statuses']=dict(Counter(str(v.get('status','UNKNOWN')) for v in homes))
            entry['sample_fields']=sorted(homes[0]) if homes else []
            entry['community_sample_fields']=sorted(communities[0]) if communities else []
        else:
            entry['html_tables']=len(soup.find_all('table'))
        return entry
    except Exception as exc:
        report['errors'].append({'url':url,'error':str(exc)[:350]})
        return None

first=fetch(INV)
# One community is enough to prove community-page access. Expand later only after verification.
community=os.environ.get('LENNAR_PROBE_COMMUNITY','https://www.lennar.com/new-homes/florida/orlando/saint-cloud/bridgewalk')
second=fetch(community)
report['ready_for_full_import']=bool(first and first.get('next_data') and first['homesite_objects']>=50 and second and second.get('next_data') and second['community_objects']>=1)
with open('lennar_probe_report.json','w',encoding='utf-8') as f:json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
if not report['ready_for_full_import']:
    print('READ-ONLY PROBE INCOMPLETE: do not enable publishing.',file=sys.stderr)
    sys.exit(1)
