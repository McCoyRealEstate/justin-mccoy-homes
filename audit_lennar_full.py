#!/usr/bin/env python3
"""Read-only Lennar structured-data audit. Never modifies or publishes the website."""
import collections, datetime, json, re, sys, urllib.parse
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE='https://www.lennar.com/new-homes/florida/orlando/'
INV=BASE+'promo/olhlen_nhc_inventory'
s=requests.Session()
s.headers.update({'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Accept-Language':'en-US,en;q=0.9'})
report={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'READ ONLY; no publishing or file changes','inventory':{},'communities':[],'summary':{},'errors':[],'warnings':[]}

def read_page(url):
    r=s.get(url,timeout=45);r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser');tag=soup.find('script',id='__NEXT_DATA__')
    if not tag or not tag.string:raise ValueError('Missing __NEXT_DATA__')
    obj=json.loads(tag.string);state=obj.get('props',{}).get('pageProps',{}).get('initialApolloState')
    if not isinstance(state,dict) or not state:raise ValueError('Missing initialApolloState')
    return state,{'status':r.status_code,'bytes':len(r.content),'final_url':r.url}

def objects(state,kind):
    return [(key,v) for key,v in state.items() if isinstance(v,dict) and (v.get('__typename')==kind or kind in key)]

def ref_value(state,ref):
    if isinstance(ref,dict):
        key=ref.get('__ref');return state.get(key,{}) if key else ref
    return {}

def collection_of(state,h):
    plan=ref_value(state,h.get('plan'))
    community=ref_value(state,plan.get('community'))
    return community.get('url') or '', plan.get('name') or h.get('planName') or ''

def canonical(url):
    if not url:return ''
    p=urllib.parse.urlparse(urllib.parse.urljoin(BASE,url)).path
    return p.rstrip('/').lower()

def lot(h):return str(h.get('lotid') or h.get('lot') or '').strip().lower()

def image_url(h):
    image=h.get('elevationImage') or {}
    return image.get('image',{}).get('url','') if isinstance(image,dict) and isinstance(image.get('image'),dict) else ''

try:
    inventory_state,meta=read_page(INV);homes=[v for _,v in objects(inventory_state,'HomesiteType')]
    available=[h for h in homes if h.get('status') in ('MOVE_IN_READY','UNDER_CONSTRUCTION')]
    report['inventory']={**meta,'homesite_objects':len(homes),'available':len(available),'statuses':dict(collections.Counter(h.get('status') for h in homes)),'with_full_lot_id':sum(len(lot(h))>4 for h in available),'with_direct_url':sum(bool(h.get('url')) for h in available),'with_photo_url':sum(bool(image_url(h)) and 'comingsoon.jpg' not in image_url(h).lower() for h in available),'plan_collection_resolved':sum(bool(collection_of(inventory_state,h)[0]) for h in available)}
    if len(available)<50:raise ValueError('Inventory returned fewer than 50 available homes')
except Exception as e:
    report['errors'].append({'stage':'inventory','message':str(e)});available=[]

# Community URLs are read from a committed baseline HTML, not invented.
try:
    text=Path('index.html').read_text(encoding='utf-8')
    match=re.search(r'\bconst\s+D\s*=\s*(\{[^\n]*\})\s*;',text)
    if not match:raise ValueError('Cannot locate const D in index.html')
    d=json.loads(match.group(1));communities=d['c'];existing=d['h']
    report['baseline']={'communities':len(communities),'homes':len(existing),'coming_soon':sum(h.get('s') in ('S','C') for h in existing)}
except Exception as e:
    report['errors'].append({'stage':'baseline','message':str(e)});communities=[];existing=[]

seen_lots=set();fees={};collected_soon=[];community_results={}
for c in communities:
    url=c.get('url')
    entry={'id':c.get('id'),'name':c.get('n'),'url':url,'loaded':False}
    try:
        state,meta=read_page(url)
        homes=[v for _,v in objects(state,'HomesiteType')]
        cols=[v for _,v in objects(state,'CommunityType')]
        entry.update(meta);entry['homesite_objects']=len(homes);entry['collection_objects']=len(cols)
        entry['statuses']=dict(collections.Counter(h.get('status') for h in homes))
        entry['coming_soon']=sum(h.get('status')=='COMING_SOON' for h in homes)
        entry['collection_fee_records']=sum(bool(x.get('url')) and x.get('hoaFee') is not None for x in cols)
        entry['resolved_plan_collections']=sum(bool(collection_of(state,h)[0]) for h in homes)
        entry['loaded']=bool(homes and cols)
        entry['collection_fee_samples']=[{'collection':x.get('url'),'hoaFee':x.get('hoaFee'),'taxRate':x.get('taxRate')} for x in cols if x.get('url')][:3]
        for x in cols:
            key=canonical(x.get('url'))
            if key:fees[key]={'hoa':x.get('hoaFee'),'tax':x.get('taxRate'),'source_community':c.get('id')}
        for h in homes:
            if h.get('status')=='COMING_SOON':
                col,plan=collection_of(state,h)
                collected_soon.append({'lot':lot(h),'address':h.get('address'),'community':c.get('id'),'collection':col,'plan':plan})
            if lot(h):seen_lots.add(lot(h))
        if not entry['loaded']:report['warnings'].append(f"{c.get('n')}: page lacked homesites or collections; do not use for removals")
    except Exception as e:
        entry['error']=str(e);report['errors'].append({'stage':'community','community':c.get('id'),'message':str(e)})
    report['communities'].append(entry);community_results[c.get('id')]=entry

inv_lots={lot(h) for h in available}
all_lots=inv_lots|seen_lots
existing_soon=[h for h in existing if h.get('s') in ('S','C')]
possible_removed=[{'lot':lot(h),'address':h.get('a'),'community':h.get('cm')} for h in existing_soon if lot(h) not in all_lots and community_results.get(h.get('cm'),{}).get('loaded')]
unchecked=[{'lot':lot(h),'address':h.get('a'),'community':h.get('cm')} for h in existing_soon if lot(h) not in all_lots and not community_results.get(h.get('cm'),{}).get('loaded')]
new_soon=[h for h in collected_soon if h['lot'] and h['lot'] not in {lot(x) for x in existing}]
missing_fee=[];mismatched=[]
for h in available:
    col,_=collection_of(inventory_state,h);key=canonical(col)
    fee=fees.get(key)
    if not fee:missing_fee.append({'lot':lot(h),'address':h.get('address'),'collection':col})
    elif fee['source_community'] not in key.split('/'): mismatched.append(lot(h))
report['summary']={'communities_checked':len(report['communities']),'communities_loaded':sum(x['loaded'] for x in report['communities']),'coming_soon_found_on_community_pages':len(collected_soon),'distinct_coming_soon_lots':len({x['lot'] for x in collected_soon if x['lot']}),'new_coming_soon_candidates':new_soon,'coming_soon_removal_candidates_NOT_APPLIED':possible_removed,'coming_soon_unchecked_NOT_APPLIED':unchecked,'collections_with_fee_records':len(fees),'available_homes_without_matched_collection_fee':missing_fee,'collection_community_mismatches':mismatched,'photo_urls_present':report.get('inventory',{}).get('with_photo_url',0),'photo_download_tested':False,'publish_performed':False}
report['ready_for_next_phase']=not report['errors'] and len(available)>=50 and sum(x['loaded'] for x in report['communities'])==len(communities) and not mismatched and not possible_removed and not new_soon
Path('lennar_full_audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'inventory':report['inventory'],'baseline':report.get('baseline'),'summary':{k:(len(v) if isinstance(v,list) else v) for k,v in report['summary'].items()},'errors':report['errors'],'warnings':report['warnings'],'ready_for_next_phase':report['ready_for_next_phase']},indent=2))
print('Full details saved to lennar_full_audit.json (download from workflow artifacts).')
if not report['ready_for_next_phase']:sys.exit(1)
