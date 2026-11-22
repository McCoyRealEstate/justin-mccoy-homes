#!/usr/bin/env python3
"""Idempotent photo-lookup finalizer for scheduled Lennar publishing."""
import json,re,sys
from pathlib import Path
OLD='let i = HIMG[h.lot] ?? HIMG[h.lot.toUpperCase()];'
NEW='let i = HIMG[h.lot] ?? HIMG[h.lot.toLowerCase()] ?? HIMG[h.lot.toUpperCase()];'
folder=Path('lennar_preview')
src=(folder/'index-phase6-unpublished.html').read_text()
if src.count(OLD)==1 and src.count(NEW)==0:
    dst=src.replace(OLD,NEW,1); status='patched'
elif src.count(NEW)==1 and src.count(OLD)==0:
    dst=src;status='already_correct'
else:
    raise SystemExit('Unsafe/unknown photo lookup state')
def const(name):
    m=re.search(r'(?m)^const\s+'+name+r'\s*=\s*',dst)
    if not m:raise ValueError('Missing '+name)
    return json.JSONDecoder().raw_decode(dst[m.end():])[0]
D,HIMG,PH,PLANPH,IMG=[const(k) for k in ('D','HIMG','PH','PLANPH','IMG')]
fail=[]
for h in D['h']:
    lot=str(h['lot']);cm=h['cm'];plan=str(h.get('pl','')).lower()
    idx=next((HIMG[k] for k in (lot,lot.lower(),lot.upper()) if k in HIMG),None)
    valid=lambda x:isinstance(x,int) and 0<=x<len(PH) and bool(PH[x])
    fallback=PLANPH.get(cm+'|'+plan,PLANPH.get(plan))
    if not(valid(idx) or valid(fallback) or cm in IMG):fail.append(lot)
if fail:raise SystemExit('No photo fallback for: '+','.join(fail))
(folder/'index-phase8-candidate.html').write_text(dst)
report={'passed':True,'photo_lookup':status,'homes':len(D['h']),'communities':len(D['c']),'photos':len(PH),'photo_or_fallback_valid_for_all_homes':True}
(folder/'phase8-finalize-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
