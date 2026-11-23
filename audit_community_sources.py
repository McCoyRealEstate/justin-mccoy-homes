"""Read-only discovery audit. Never changes published inventory."""
import json,re,requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
from pathlib import Path
BASE="https://www.lennar.com/new-homes/florida/orlando"
session=requests.Session()
session.headers["User-Agent"]="Mozilla/5.0 Chrome/131.0.0.0 Safari/537.36"
def read(url):
    r=session.get(url,timeout=60);r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    tag=soup.find("script",id="__NEXT_DATA__")
    if not tag: raise RuntimeError("Missing source data: "+url)
    state=json.loads(tag.string)["props"]["pageProps"]["initialApolloState"]
    return state,soup
def community_url(url):
    p=urlparse(urljoin(BASE+"/",url or ""))
    parts=p.path.strip("/").split("/")
    if p.hostname not in ("www.lennar.com","lennar.com") or parts[:3]!=["new-homes","florida","orlando"]: return None
    if len(parts)<5 or parts[3] in ("promo","brochure"): return None
    return BASE+"/"+"/".join(parts[3:5])
def candidates(state,soup):
    result=set()
    for v in state.values():
        if isinstance(v,dict) and v.get("__typename")=="CommunityType":
            u=community_url(v.get("url"))
            if u: result.add(u)
    for a in soup.find_all("a",href=True):
        u=community_url(a["href"])
        if u: result.add(u)
    return result
def main():
    html=Path("index.html").read_text()
    m=re.search(r"(?m)^const\s+D\s*=\s*",html)
    baseline=json.JSONDecoder().raw_decode(html[m.end():])[0]
    old={community_url(c["url"]) for c in baseline["c"]}
    sources={}
    for url in (BASE,BASE+"/promo/olhlen_nhc_inventory"):
        st,soup=read(url)
        sources[url]=candidates(st,soup)
    found=set.union(*sources.values())
    if len(found)<max(10,len(old)//2): raise RuntimeError("Discovery incomplete")
    records=[]
    for url in sorted(found|old):
        try:
            st,_=read(url)
            objs=[v for v in st.values() if isinstance(v,dict) and v.get("__typename")=="CommunityType" and community_url(v.get("url"))==url]
            records.append({"url":url,"known":url in old,"discovered":url in found,"community_objects":objs,"homes":[{"lot":v.get("lotid"),"status":v.get("status")} for v in st.values() if isinstance(v,dict) and v.get("__typename")=="HomesiteType"]})
        except Exception as e:
            records.append({"url":url,"error":str(e)})
    report={"baseline":sorted(old),"sources":{k:sorted(v) for k,v in sources.items()},"new_candidates":sorted(found-old),"missing_candidates":sorted(old-found),"records":records}
    Path("community-audit.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!="records"},indent=2))
if __name__=="__main__": main()
