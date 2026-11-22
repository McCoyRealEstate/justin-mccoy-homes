#!/usr/bin/env python3
"""Phase 4: generate an UNPUBLISHED Lennar HTML preview. Never edits index.html."""
import base64, collections, copy, datetime, hashlib, io, json, re, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

BASE="https://www.lennar.com/new-homes/florida/orlando/"
INV=BASE+"promo/olhlen_nhc_inventory"
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"lennar_preview"
OUT.mkdir(exist_ok=True)
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36","Accept-Language":"en-US,en;q=0.9"})
report={"mode":"DRY RUN; index.html never modified","utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"errors":[],"warnings":[]}

def fail(msg): raise RuntimeError(msg)
def line(text,key):
    m=re.search(r"(?m)^(const\s+"+re.escape(key)+r"\s*=\s*)",text)
    if not m: fail("Missing const "+key)
    value,end=json.JSONDecoder().raw_decode(text[m.end():])
    return value,(m.end(),m.end()+end)
def put(text,key,val):
    _,(a,b)=line(text,key)
    return text[:a]+json.dumps(val,separators=(",",":"),ensure_ascii=False)+text[b:]
def read(url):
    r=s.get(url,timeout=50);r.raise_for_status()
    tag=BeautifulSoup(r.text,"html.parser").find("script",id="__NEXT_DATA__")
    if not tag or not tag.string: fail("No NEXT_DATA: "+url)
    st=json.loads(tag.string)["props"]["pageProps"]["initialApolloState"]
    if not isinstance(st,dict) or not st:fail("Empty Apollo state: "+url)
    return st
def objects(st,kind):
    return [v for v in st.values() if isinstance(v,dict) and v.get("__typename")==kind]
def resolve(st,x):
    return st.get(x["__ref"],{}) if isinstance(x,dict) and x.get("__ref") else (x if isinstance(x,dict) else {})
def coll(st,h):
    plan=resolve(st,h.get("plan"))
    return resolve(st,plan.get("community")).get("url","")
def canon(url):
    return urlparse(urljoin(BASE,url or "")).path.rstrip("/").lower()
def lot(h):return str(h.get("lotid") or h.get("lot") or "").strip().lower()
def cmid(url):
    a=canon(url).split("/")
    # /new-homes/florida/orlando/{city}/{community}/{collection}
    try:
        i=a.index("orlando")
        return a[i+2]
    except (ValueError,IndexError):return ""
def photo(h):
    e=h.get("elevationImage") or {}
    return (e.get("image") or {}).get("url","") if isinstance(e,dict) and isinstance(e.get("image"),dict) else ""
def safephoto(url):
    return bool(url) and "comingsoon" not in url.lower() and urlparse(urljoin("https://cdn.lennar.com/",url)).hostname in ("cdn.lennar.com","www.lennar.com","lennar.com")
def image_data(url):
    u=urljoin("https://cdn.lennar.com/",url)
    r=s.get(u,timeout=45,headers={"Referer":"https://www.lennar.com/"},stream=True)
    r.raise_for_status()
    data=r.raw.read(15_000_001)
    r.close()
    if len(data)>15_000_000:fail("Oversized image")
    with Image.open(io.BytesIO(data)) as src:
        src.load()
        im=ImageOps.exif_transpose(src).convert("RGB")
        if min(im.size)<100:fail("Small image")
        height=round(im.height*360/im.width)
        if not 80<=height<=2000:fail("Bad image aspect")
        im=im.resize((360,height),Image.Resampling.LANCZOS)
        buf=io.BytesIO()
        im.save(buf,format="JPEG",quality=62,optimize=True)
        binary=buf.getvalue()
    with Image.open(io.BytesIO(binary)) as check:check.verify()
    return "data:image/jpeg;base64,"+base64.b64encode(binary).decode()
def listing_url(h,full):
    u=h.get("url") or ""
    path=canon(u)
    prefix=canon(BASE)+"/"
    if not path.startswith(prefix) or path.split("/")[-1]!=full: fail("Unverified listing URL for "+full)
    return path[len(prefix):]
def safe_num(x,default=None):
    if x is None:return default
    try:
        return float(x) if isinstance(x,str) and "." in x else int(x)
    except (ValueError,TypeError):return default

try:
    original=(ROOT/"index.html").read_text(encoding="utf-8")
    D,_=line(original,"D"); LU,_=line(original,"LU")
    PH,_=line(original,"PH"); HIMG,_=line(original,"HIMG"); PLANPH,_=line(original,"PLANPH")
    IMG,_=line(original,"IMG")
    for name,value in (("D",D),("LU",LU),("HIMG",HIMG),("PLANPH",PLANPH),("IMG",IMG)):
        if not isinstance(value,dict):fail(name+" should be an object")
    if not isinstance(PH,list):fail("PH should be array")
    before=copy.deepcopy(D)
    communities={c["id"]:c for c in D["c"]}
    oldhomes={lot(h):h for h in D["h"]}
    if len(oldhomes)!=len(D["h"]):fail("Duplicate baseline lot IDs")
    available_old={k for k,h in oldhomes.items() if h.get("s") not in ("S","C")}
    soon_old={k for k,h in oldhomes.items() if h.get("s") in ("S","C")}
    st=read(INV)
    available=[h for h in objects(st,"HomesiteType") if h.get("status") in ("MOVE_IN_READY","UNDER_CONSTRUCTION")]
    if len(available)<max(50,len(available_old)*.5):fail("Inventory appears truncated")
    if len({lot(h) for h in available})!=len(available):fail("Duplicate source lots")
    page_states={}
    fees={}
    soon={}
    for c in D["c"]:
        state=read(c["url"])
        ch=objects(state,"HomesiteType")
        if not ch:fail("Community page empty: "+c["id"])
        page_states[c["id"]]=state
        for obj in objects(state,"CommunityType"):
            url=canon(obj.get("url"))
            if url and cmid(url)==c["id"]:
                fees[url]={"hoa":obj.get("hoaFee"),"tax":obj.get("taxRate"),"community":c["id"]}
        for h in ch:
            if h.get("status")=="COMING_SOON":
                k=lot(h)
                if not k or (k in soon and soon[k][0]!=c["id"]):fail("Duplicate Coming Soon lot")
                soon[k]=(c["id"],h,state)
    report["source"]={"available":len(available),"coming_soon":len(soon),"communities":len(page_states),"fee_records":len(fees),"photo_urls":sum(safephoto(photo(h)) for h in available)}
    if len(page_states)!=len(communities):fail("Not all community pages loaded")
    if len(soon)<max(5,len(soon_old)*.5):fail("Coming Soon count unexpectedly low")
    # For this first full preview, do not remove ANY existing homes.
    D=copy.deepcopy(D);LU=copy.deepcopy(LU);PH=list(PH);HIMG=dict(HIMG);PLANPH=dict(PLANPH)
    newhomes={lot(h):h for h in D["h"]}
    added=changed=0
    photos_added=photo_failed=0
    photo_cache={}
    fee_unknown=[]
    source_lots=set()
    entries=[(h,st,None) for h in available]+[(h,cs,cid) for cid,h,cs in soon.values()]
    for src,state,declared_cid in entries:
        k=lot(src); source_lots.add(k)
        col=canon(coll(state,src))
        cid=cmid(col)
        if cid not in communities:fail("Unknown community/collection for "+k+": "+col)
        if declared_cid and cid!=declared_cid:fail("Coming Soon community mismatch for "+k)
        url=listing_url(src,k)
        is_soon=src.get("status")=="COMING_SOON"
        status="S" if is_soon else ("M" if src["status"]=="MOVE_IN_READY" else "U")
        home=newhomes.get(k)
        if home is None:
            home={"lot":k,"cm":cid,"g":0,"miss":0}
            D["h"].append(home);newhomes[k]=home;added+=1
        else:
            if home["cm"]!=cid:fail("Existing home moved communities: "+k)
        old=copy.deepcopy(home)
        # Keep existing garage and any other non-source fields unchanged.
        plan=resolve(state,src.get("plan"))
        changes={"a":src.get("address") or home.get("a"),"s":status,"bd":safe_num(src.get("beds"),home.get("bd")),"ba":safe_num(src.get("baths"),0)+.5*safe_num(src.get("halfBaths"),0),"sq":safe_num(src.get("sqft"),home.get("sq")),"pl":src.get("planName") or plan.get("name") or home.get("pl"),"miss":0}
        if not is_soon:
            price=safe_num(src.get("price"))
            if price is None or not 100000<=price<=2000000:fail("Invalid price "+k)
            changes["p"]=price
            changes["w"]=safe_num(src.get("wasPrice"),price) or price
        # Preserve Coming Soon price masking, including the original JS enforcement.
        if is_soon:changes["np"]=1
        else:changes.pop("np",None)
        home.update(changes)
        if not is_soon:home.pop("np",None)
        fee=fees.get(col)
        if fee and fee["community"]==cid:
            if fee["hoa"] is not None:home["hoa"]=fee["hoa"]
            else:home["hoa"]=None
            if fee["tax"] is not None:home["tax"]=fee["tax"]
            else:home.pop("tax",None)
        else:
            home["hoa"]=None;home.pop("tax",None)
            fee_unknown.append({"lot":k,"collection":col})
        LU[k]=url
        if home!=old:changed+=1
        if not is_soon and safephoto(photo(src)):
            source=photo(src)
            try:
                if source not in photo_cache:photo_cache[source]=image_data(source)
                uri=photo_cache[source]
                # Reuse identical image payloads, never overwrite prior entries.
                try:idx=PH.index(uri)
                except ValueError:
                    idx=len(PH);PH.append(uri);photos_added+=1
                HIMG[k]=idx
                pname=str(home.get("pl") or "").lower().strip()
                if pname:
                    PLANPH[cid+"|"+pname]=idx
                    PLANPH.setdefault(pname,idx)
            except Exception as exc:
                photo_failed+=1
                report["warnings"].append("Photo download failed for "+k+": "+str(exc)[:100])
    missing_existing=sorted(set(oldhomes)-source_lots)
    report["warnings"].append(str(len(missing_existing))+" existing homes absent from source; all retained pending separate verification") if missing_existing else None
    if photo_failed>max(3,int(len(available)*.10)):fail("Too many failed photo downloads")
    if len(fee_unknown)>3:fail("Too many unknown collection fees: "+str(len(fee_unknown)))
    if len({lot(h) for h in D["h"]})!=len(D["h"]):fail("Duplicate final lot IDs")
    if any(h["cm"] not in communities for h in D["h"]):fail("Orphaned community")
    if any(not isinstance(idx,int) or idx<0 or idx>=len(PH) for idx in HIMG.values()):fail("Invalid HIMG index")
    if any(not isinstance(idx,int) or idx<0 or idx>=len(PH) for idx in PLANPH.values()):fail("Invalid PLANPH index")
    for k,v in LU.items():
        if canon(v).split("/")[-1]!=str(k).lower():fail("Invalid listing link "+k)
    new=original
    for key,value in (("D",D),("LU",LU),("PH",PH),("HIMG",HIMG),("PLANPH",PLANPH)):
        new=put(new,key,value)
    new=put(new,"IMPORTED",report["utc"])
    try:
        from zoneinfo import ZoneInfo
        date=datetime.datetime.now(ZoneInfo("America/New_York"))
    except Exception:date=datetime.datetime.now(datetime.timezone.utc)
    new=put(new,"UPDATED",date.strftime("%B %d, %Y").replace(" 0"," "))
    # Exact preservation of all non-data code and community monuments.
    sentinel="__DATA_CONSTANT__"
    def skeleton(txt):
        for key in ("D","LU","PH","HIMG","PLANPH","IMPORTED","UPDATED"):
            _,(a,b)=line(txt,key)
            txt=txt[:a]+sentinel+txt[b:]
        return txt
    if skeleton(original)!=skeleton(new):fail("Non-data HTML/JS changed")
    if line(new,"IMG")[0]!=IMG:fail("Community images changed")
    if 'if (h.s === "S" || h.s === "C") h.np = 1' not in new:
        fail("Coming Soon price-masking guard missing")
    if len(new)>20_000_000:fail("Preview HTML unusually large")
    report["result"]={"baseline_homes":len(oldhomes),"new_homes":len(D["h"]),"added":added,"changed":changed,"removed":0,"missing_existing_retained":missing_existing,"photos_new_in_library":photos_added,"photo_download_failures":photo_failed,"unknown_collection_fees":fee_unknown,"html_bytes":len(new),"original_sha256":hashlib.sha256(original.encode()).hexdigest(),"preview_sha256":hashlib.sha256(new.encode()).hexdigest(),"publish_performed":False}
    (OUT/"index-preview.html").write_text(new,encoding="utf-8")
    report["passed"]=True
except Exception as exc:
    report["errors"].append(str(exc))
    report["passed"]=False
(OUT/"preview-report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(report,indent=2,ensure_ascii=False))
if not report["passed"]:sys.exit(1)
