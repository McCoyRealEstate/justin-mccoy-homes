import json,re,base64,io
from pathlib import Path
from collections import Counter
from PIL import Image
html=Path("lennar_preview/index-preview.html").read_text()
def const(k):
    m=re.search(r"(?m)^const\s+"+k+r"\s*=\s*",html)
    return json.JSONDecoder().raw_decode(html[m.end():])[0]
D,PH,HIMG,PLANPH,IMG=[const(k) for k in ("D","PH","HIMG","PLANPH","IMG")]
def valid(v):
    if type(v) is int:
        return 0<=v<len(PH) and valid(PH[v])
    if not isinstance(v,str):return False
    if v.startswith("data:image/"):
        try:
            with Image.open(io.BytesIO(base64.b64decode(v.split(",",1)[1]))) as im:im.verify()
            return True
        except Exception:return False
    return v.startswith(("https://cdn.lennar.com/","https://lennar.bynder.com/","https://www.lennar.com/"))
def choose(h,own,plans,monuments):
    lot=str(h["lot"]);key=h["cm"]+"|"+str(h.get("pl","")).strip().lower()
    for k in (lot,lot.lower(),lot.upper()):
        if valid(own.get(k)):return "listing"
    if valid(plans.get(key)):return "same_community_plan"
    if valid(monuments.get(h["cm"])):return "monument"
    return "missing"
sample={"lot":"test","cm":"a","pl":"Test"}
assert choose(sample,{"test":0},{"a|test":0},{"a":0})=="listing"
assert choose(sample,{},{"a|test":0},{"a":0})=="same_community_plan"
assert choose(sample,{},{"b|test":0,"test":0},{"a":0})=="monument"
assert choose(sample,{"test":-1},{"a|test":0},{"a":0})=="same_community_plan"
counts=Counter(choose(h,HIMG,PLANPH,IMG) for h in D["h"])
missing=[h["lot"] for h in D["h"] if choose(h,HIMG,PLANPH,IMG)=="missing"]
report={"counts":dict(counts),"missing":missing,"communities":len(D["c"]),"simulated_tests":4}
print(json.dumps(report,indent=2))
Path("lennar_preview/photo-hierarchy-report.json").write_text(json.dumps(report,indent=2))
assert not missing, "Listings without verified image fallback"
