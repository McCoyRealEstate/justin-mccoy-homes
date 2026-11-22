#!/usr/bin/env python3
"""Phase 6: read-only publish candidate. Never edits index.html or commits."""
import copy, datetime, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'lennar_preview'; OUT.mkdir(exist_ok=True)
report={'mode':'PHASE 6 DRY RUN — NO PUBLISH','timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'errors':[],'warnings':[]}

def constant(text,key):
    m=re.search(r'(?m)^(const\s+'+re.escape(key)+r'\s*=\s*)',text)
    if not m: raise ValueError('Missing '+key)
    value,end=json.JSONDecoder().raw_decode(text[m.end():])
    return value,(m.end(),m.end()+end)

def replace(text,key,value):
    _,(a,b)=constant(text,key)
    return text[:a]+json.dumps(value,separators=(',',':'),ensure_ascii=False)+text[b:]

def fingerprint(text):
    for key in ('D','LU','PH','HIMG','PLANPH','IMPORTED','UPDATED'):
        _,(a,b)=constant(text,key)
        text=text[:a]+'__DATA__'+text[b:]
    return text

try:
    original=(ROOT/'index.html').read_text(encoding='utf-8')
    candidate=(OUT/'index-normalized-unpublished.html').read_text(encoding='utf-8')
    p4=json.loads((OUT/'preview-report.json').read_text())
    p5=json.loads((OUT/'verification-report.json').read_text())
    if not p4.get('passed') or not p5.get('passed'):raise ValueError('Prior preview or verification did not pass')
    if p4.get('result',{}).get('publish_performed') is not False:raise ValueError('Preview unexpectedly published')
    baseline_sha=hashlib.sha256(original.encode()).hexdigest()
    if p4['result']['original_sha256']!=baseline_sha:raise ValueError('Baseline changed between preview and Phase 6')
    if fingerprint(original)!=fingerprint(candidate):raise ValueError('Website layout, branding or non-data code differs')
    for key in ('IMG',):
        if constant(original,key)[0]!=constant(candidate,key)[0]:raise ValueError('Community images changed')
    old=constant(original,'D')[0]; new=copy.deepcopy(constant(candidate,'D')[0])
    oldhomes={str(h['lot']).lower():h for h in old['h']}
    newhomes={str(h['lot']).lower():h for h in new['h']}
    if len(oldhomes)!=len(old['h']) or len(newhomes)!=len(new['h']):raise ValueError('Duplicate lot IDs')
    absent=set(p4['result']['missing_existing_retained'])
    listings={str(x['lot']).lower():x for x in p5['listings']}
    if absent!=set(listings):raise ValueError('Missing homes were not all verified')
    if len(absent)>15:raise ValueError('Safety limit exceeded: more than 15 removals')
    allowed={'lot_not_in_page_data','absent_from_community_page'}
    confirmed=[];hold=[]
    for lot in sorted(absent):
        item=listings[lot]
        classification=item.get('classification')
        if classification=='lot_not_in_page_data':
            ok=(item.get('http_status')==200 and item.get('redirected') is True and item.get('matching_homesite_objects')==0 and item.get('final_path_matches_lot') is False)
        elif classification=='absent_from_community_page':
            ok=(item.get('http_status')==200 and item.get('matching_homesite_objects')==0 and item.get('direct_listing_available') is False)
        else:ok=False
        if ok and lot in newhomes:confirmed.append(lot)
        else:hold.append({'lot':lot,'classification':classification})
    if hold:raise ValueError('Removal verification incomplete; fail closed: '+json.dumps(hold))
    # Remove ONLY the independently verified missing homes.
    new['h']=[h for h in new['h'] if str(h['lot']).lower() not in confirmed]
    for h in new['h']:
        if h.get('s') in ('S','C'):h['np']=1
        else:h.pop('np',None)
    remaining={str(h['lot']).lower():h for h in new['h']}
    lu=copy.deepcopy(constant(candidate,'LU')[0]); himg=copy.deepcopy(constant(candidate,'HIMG')[0])
    for lot in confirmed:
        lu.pop(lot,None);himg.pop(lot,None)
    if any(lot in lu or lot in himg or lot in remaining for lot in confirmed):raise ValueError('Removal left dangling home-specific references')
    if len(remaining)<100:raise ValueError('Unexpected inventory shrinkage')
    if len(new['c'])!=len(old['c']) or len(new['c'])!=25:raise ValueError('Community count changed')
    if any(h['cm'] not in {c['id'] for c in new['c']} for h in new['h']):raise ValueError('Orphan community')
    if any(h.get('np')!=1 for h in new['h'] if h.get('s') in ('S','C')):raise ValueError('Coming Soon price mask missing')
    for lot in remaining:
        if lot not in lu:raise ValueError('Missing listing link: '+lot)
    # Compare exact baseline and candidate changes, do not publish.
    added=sorted(set(remaining)-set(oldhomes));removed=sorted(set(oldhomes)-set(remaining))
    changed=sorted(lot for lot in set(oldhomes)&set(remaining) if oldhomes[lot]!=remaining[lot])
    if removed!=sorted(confirmed):raise ValueError('Unexpected removals')
    if len(added)>30:raise ValueError('Unexpectedly many additions')
    result=candidate
    for key,val in [('D',new),('LU',lu),('HIMG',himg)]:result=replace(result,key,val)
    if fingerprint(result)!=fingerprint(original):raise ValueError('Non-data website code changed')
    if constant(result,'IMG')[0]!=constant(original,'IMG')[0]:raise ValueError('Community monuments changed')
    if 'if (h.s === "S" || h.s === "C") h.np = 1' not in result:raise ValueError('Runtime price guard absent')
    if len(result)>20_000_000:raise ValueError('HTML size safety limit exceeded')
    (OUT/'index-phase6-unpublished.html').write_text(result,encoding='utf-8')
    report.update({'passed':True,'live_site_modified':False,'baseline_sha256':baseline_sha,'candidate_sha256':hashlib.sha256(result.encode()).hexdigest(),
      'baseline_homes':len(oldhomes),'candidate_homes':len(remaining),'communities':len(new['c']),
      'added':[{'lot':k,'address':remaining[k].get('a'),'community':remaining[k].get('cm'),'status':remaining[k].get('s')} for k in added],
      'removed':[{'lot':k,'address':oldhomes[k].get('a'),'community':oldhomes[k].get('cm'),'last_status':oldhomes[k].get('s'),'verification':listings[k]['classification']} for k in removed],
      'updated_count':len(changed),'updated_examples':[{'lot':k,'address':remaining[k].get('a'),'before':{x:oldhomes[k].get(x) for x in ('s','p','hoa','tax')},'after':{x:remaining[k].get(x) for x in ('s','p','hoa','tax')}} for k in changed[:20]],
      'coming_soon_count':sum(h.get('s') in ('S','C') for h in new['h']),
      'move_in_ready_count':sum(h.get('s')=='M' for h in new['h']),
      'under_construction_count':sum(h.get('s')=='U' for h in new['h']),
      'photo_library_count':len(constant(result,'PH')[0]),'removed_limit':15})
except Exception as exc:
    report['passed']=False;report['errors'].append(str(exc))
(OUT/'phase6-publish-diff.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,indent=2,ensure_ascii=False))
sys.exit(0 if report['passed'] else 1)
