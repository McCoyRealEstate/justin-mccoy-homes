#!/usr/bin/env python3
"""Phase 5 READ ONLY: inspect Phase 4 preview, verify missing listings and photo fallbacks."""
import collections, datetime, hashlib, json, re, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"lennar_preview"
OUT.mkdir(exist_ok=True)
BASE="https://www.lennar.com/new-homes/florida/orlando/"
report={"mode":"READ ONLY; no changes to live site","time_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"checks":{},"listings":[],"photo_fallbacks":[],"warnings":[],"errors":[]}
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36","Accept-Language":"en-US,en;q=0.9"})
def const(text,key):
    m=re.search(r"(?m)^(const\s+"+re.escape(key)+r"\s*=\s*)",text)
    if not m:raise ValueError("Missing "+key)
    val,end=json.JSONDecoder().raw_decode(text[m.end():])
    return val,(m.end(),m.end()+end)
def objects(st,name):
    return [v for v in st.values() if isinstance(v,dict) and v.get("__typename")==name]
def canonical(url):
    return urlparse(urljoin(BASE,url)).path.lower().rstrip("/")
def verify_lennar_listing(lot,url):
    target=urljoin(BASE,url)
    item={"lot":lot,"requested_url":target,"classification":"unverified"}
    try:
        r=s.get(target,timeout=35,allow_redirects=True)
        item["http_status"]=r.status_code
        item["final_url"]=r.url
        item["redirected"]=canonical(target)!=canonical(r.url)
        if r.status_code!=200:
            item["classification"]="http_error";return item
        soup=BeautifulSoup(r.text,"html.parser")
        tag=soup.find("script",id="__NEXT_DATA__")
        if not tag or not tag.string:
            item["classification"]="no_next_data";return item
        data=json.loads(tag.string)
        st=data.get("props",{}).get("pageProps",{}).get("initialApolloState",{})
        matches=[h for h in objects(st,"HomesiteType") if str(h.get("lotid","")).lower()==lot]
        item["matching_homesite_objects"]=len(matches)
        item["statuses"]=sorted({str(h.get("status")) for h in matches})
        item["final_path_matches_lot"]=canonical(r.url).split("/")[-1]==lot
        if matches and item["final_path_matches_lot"] and not item["redirected"]:
            item["classification"]="listing_present"
        elif matches:
            item["classification"]="lot_present_but_redirected"
        else:
            item["classification"]="lot_not_in_page_data"
    except Exception as exc:
        item["classification"]="fetch_error"
        item["error"]=str(exc)[:180]
    return item

try:
    html=(OUT/"index-preview.html").read_text(encoding="utf-8")
    data,_=const(html,"D");lu,_=const(html,"LU")
    ph,_=const(html,"PH");himg,_=const(html,"HIMG");planph,_=const(html,"PLANPH");img,_=const(html,"IMG")
    imported,_=const(html,"IMPORTED")
    homes=data["h"];bylot={str(h["lot"]).lower():h for h in homes}
    if len(bylot)!=len(homes):raise ValueError("Duplicate lots")
    baseline_report=json.loads((OUT/"preview-report.json").read_text())
    missing=baseline_report.get("result",{}).get("missing_existing_retained",[])
    report["checks"]["missing_existing_lots"]=missing
    for lot in missing:
        if lot not in bylot or lot not in lu:
            report["errors"].append("Missing retained lot or listing link: "+lot)
            continue
        item=verify_lennar_listing(lot,lu[lot])
        item["address"]=bylot[lot].get("a")
        item["community"]=bylot[lot].get("cm")
        report["listings"].append(item)
        if item["classification"]!="listing_present":
            report["warnings"].append(lot+" requires human review: "+item["classification"])
    soon=[h for h in homes if h.get("s") in ("S","C")]
    missing_mask=[h["lot"] for h in soon if h.get("np")!=1]
    report["checks"]["coming_soon_total"]=len(soon)
    report["checks"]["coming_soon_missing_stored_mask"]=missing_mask
    guard='if (h.s === "S" || h.s === "C") h.np = 1'
    report["checks"]["runtime_price_guard_present"]=guard in html
    if guard not in html:report["errors"].append("Runtime price masking guard missing")
    if missing_mask:report["warnings"].append("Some retained Coming Soon homes lack np=1; normalization preview created")
    # Produce a second *unpublished* candidate that normalizes price masking only.
    fixed=json.loads(json.dumps(data))
    for h in fixed["h"]:
        if h.get("s") in ("S","C"):h["np"]=1
        else:h.pop("np",None)
    _,(a,b)=const(html,"D")
    normalized=html[:a]+json.dumps(fixed,separators=(",",":"),ensure_ascii=False)+html[b:]
    (OUT/"index-normalized-unpublished.html").write_text(normalized,encoding="utf-8")
    report["checks"]["normalized_html_sha256"]=hashlib.sha256(normalized.encode()).hexdigest()
    report["checks"]["only_D_modified_in_normalized_candidate"]=(html[:a]==normalized[:a] and html[b:]==normalized[len(normalized)-(len(html)-b):])
    if not report["checks"]["only_D_modified_in_normalized_candidate"]:report["errors"].append("Unexpected normalization changes")
    if not isinstance(ph,list) or not isinstance(himg,dict) or not isinstance(planph,dict) or not isinstance(img,dict):
        raise ValueError("Unexpected photo structure")
    bad_refs=[]
    for k,idx in list(himg.items())+list(planph.items()):
        if not isinstance(idx,int) or not 0<=idx<len(ph):bad_refs.append(k)
    if bad_refs:report["errors"].append("Invalid photo indexes: "+str(bad_refs[:10]))
    no_own=[h for h in homes if h.get("s") not in ("S","C") and h["lot"] not in himg]
    for h in no_own:
        cid=h["cm"];plan=str(h.get("pl") or "").strip().lower()
        key=cid+"|"+plan
        if key in planph:typ="same_community_plan";idx=planph[key]
        elif plan in planph:typ="general_plan";idx=planph[plan]
        elif cid in img:typ="community_monument";idx=None
        else:typ="missing_fallback";idx=None
        record={"lot":h["lot"],"address":h.get("a"),"plan":h.get("pl"),"community":cid,"fallback_type":typ}
        if idx is not None:record["photo_index"]=idx
        report["photo_fallbacks"].append(record)
        if typ=="missing_fallback":report["errors"].append("No fallback for "+h["lot"])
    # Duplicate photos may be legitimate shared renderings; report but do not fail.
    photo_groups=collections.defaultdict(list)
    for lot,idx in himg.items():photo_groups[idx].append(lot)
    shared=[{"photo_index":idx,"lots":lots} for idx,lots in photo_groups.items() if len(lots)>1]
    report["checks"]["shared_photo_groups"]=shared[:30]
    report["checks"]["available_without_own_photo"]=len(no_own)
    report["checks"]["all_coming_soon_masked_in_normalized_candidate"]=all(h.get("np")==1 for h in fixed["h"] if h.get("s") in ("S","C"))
    report["checks"]["live_site_modified"]=False
    report["passed"]=not report["errors"]
except Exception as exc:
    report["errors"].append(str(exc))
    report["passed"]=False
(OUT/"verification-report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(report,indent=2,ensure_ascii=False))
sys.exit(0 if report["passed"] else 1)
