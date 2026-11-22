#!/usr/bin/env python3
"""Read-only Phase 6 photo-lookup patch. Does not edit index.html or publish."""
import argparse, json, re, sys
from pathlib import Path

OLD='let i = HIMG[h.lot] ?? HIMG[h.lot.toUpperCase()];'
NEW='let i = HIMG[h.lot] ?? HIMG[h.lot.toLowerCase()] ?? HIMG[h.lot.toUpperCase()];'

def constant(src,name):
    m=re.search(r'(?m)^const\s+'+re.escape(name)+r'\s*=\s*',src)
    if not m: raise ValueError(f'Missing {name} constant')
    return json.JSONDecoder().raw_decode(src[m.end():])[0]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',default='lennar_preview/index-phase6-unpublished.html')
    ap.add_argument('--output',default='lennar_preview/index-phase6-photo-fixed-unpublished.html')
    args=ap.parse_args()
    src=Path(args.input).read_text(encoding='utf-8')
    count=src.count(OLD)
    if count != 1: raise ValueError(f'Expected one original lookup, found {count}; refuse to modify')
    dst=src.replace(OLD,NEW,1)
    D=constant(dst,'D'); HIMG=constant(dst,'HIMG'); PH=constant(dst,'PH'); PLANPH=constant(dst,'PLANPH'); IMG=constant(dst,'IMG')
    assert len(D['h'])>0 and len(PH)>0
    cases=[]; failures=[]
    for h in D['h']:
        lot=str(h['lot']); plan=str(h.get('pl','')).lower(); cm=h['cm']
        exact=HIMG.get(lot)
        idx=next((HIMG[k] for k in (lot,lot.lower(),lot.upper()) if k in HIMG),None)
        valid=idx is not None and isinstance(idx,int) and 0<=idx<len(PH) and bool(PH[idx])
        fallback=PLANPH.get(cm+'|'+plan,PLANPH.get(plan))
        fallback_valid=isinstance(fallback,int) and 0<=fallback<len(PH) and bool(PH[fallback])
        if not valid and not fallback_valid and cm not in IMG:failures.append(lot)
        if lot != lot.lower():
            cases.append({'lot':lot,'address':h.get('a'),'exact_image':exact,'resolved_image':idx if valid else None,'fallback_available':fallback_valid or cm in IMG})
    if failures:raise ValueError('Homes without photo or fallback: '+', '.join(failures))
    if dst.replace(NEW,OLD,1)!=src:raise ValueError('Unexpected changes')
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(dst,encoding='utf-8')
    report={'mode':'READ ONLY','original_home_count':len(D['h']),'uppercase_lot_records':cases,'uppercase_lot_count':len(cases),'photo_or_fallback_valid_for_all_homes':True,'only_photo_lookup_changed':True,'published':False,'output':str(out)}
    (out.parent/'phase6-photo-fix-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':
    try:main()
    except Exception as e:print('FAIL:',e,file=sys.stderr);sys.exit(1)
