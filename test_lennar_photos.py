#!/usr/bin/env python3
"""Read-only test of Lennar photo downloads and JPEG compression on GitHub Actions.
Never edits index.html or any repository file. No photos are stored in the report.
"""
import datetime, hashlib, io, json, re, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

INV = 'https://www.lennar.com/new-homes/florida/orlando/promo/olhlen_nhc_inventory'
HEADERS = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Accept-Language':'en-US,en;q=0.9'}
report={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'READ ONLY - NO PUBLISH','inventory':{},'samples':[],'errors':[],'warnings':[]}
s=requests.Session();s.headers.update(HEADERS)

def image_url(home):
    x=home.get('elevationImage') or {}
    return (x.get('image') or {}).get('url','') if isinstance(x,dict) and isinstance(x.get('image'),dict) else ''

def full_url(value):
    if value.startswith('//'): return 'https:'+value
    if value.startswith('http://') or value.startswith('https://'):return value
    return urljoin('https://cdn.lennar.com/',value.lstrip('/'))

def scaled_url(value):
    u=urlparse(value)
    if u.hostname and u.hostname.lower().endswith('lennar.com'):
        q=dict(parse_qsl(u.query,keep_blank_values=True));q['w']='720'
        return urlunparse(u._replace(query=urlencode(q)))
    return value

try:
    r=s.get(INV,timeout=45);r.raise_for_status()
    tag=BeautifulSoup(r.text,'html.parser').find('script',id='__NEXT_DATA__')
    if not tag or not tag.string:raise ValueError('Inventory lacks __NEXT_DATA__')
    state=json.loads(tag.string)['props']['pageProps']['initialApolloState']
    homes=[v for v in state.values() if isinstance(v,dict) and v.get('__typename')=='HomesiteType' and v.get('status') in ('MOVE_IN_READY','UNDER_CONSTRUCTION')]
    candidates=[h for h in homes if image_url(h) and 'comingsoon.jpg' not in image_url(h).lower()]
    report['inventory']={'status':r.status_code,'available':len(homes),'photo_urls':len(candidates)}
    if len(homes)<50 or len(candidates)<5:raise ValueError('Inventory/photo counts unexpectedly low')
    # Distinct source URLs so repeated photos do not make a misleading test.
    selected=[];used=set()
    for h in candidates:
        u=full_url(image_url(h))
        if u in used:continue
        used.add(u);selected.append((h,u))
        if len(selected)==5:break
    if len(selected)<5:raise ValueError('Fewer than five distinct photos')
    for h,u in selected:
        entry={'lot':str(h.get('lotid') or ''),'address':h.get('address'),'source_host':urlparse(u).hostname}
        try:
            resp=s.get(scaled_url(u),timeout=40,headers={'Referer':'https://www.lennar.com/'})
            resp.raise_for_status()
            if len(resp.content)>15_000_000:raise ValueError('Image larger than 15 MB')
            with Image.open(io.BytesIO(resp.content)) as src:
                src.load();entry['source_format']=src.format;entry['source_size']=list(src.size)
                if src.width<100 or src.height<100:raise ValueError('Image too small')
                im=ImageOps.exif_transpose(src).convert('RGB')
                width=360;height=max(1,round(im.height*width/im.width))
                if height>2000:raise ValueError('Unexpected image aspect ratio')
                im=im.resize((width,height),Image.Resampling.LANCZOS)
                out=io.BytesIO();im.save(out,format='JPEG',quality=62,optimize=True)
                result=out.getvalue()
            with Image.open(io.BytesIO(result)) as check:
                check.verify()
            entry.update({'download_status':resp.status_code,'download_bytes':len(resp.content),'jpeg_bytes':len(result),'jpeg_dimensions':[width,height],'jpeg_sha256_prefix':hashlib.sha256(result).hexdigest()[:12],'ok':True})
        except Exception as e:
            entry.update({'ok':False,'error':str(e)});report['errors'].append({'lot':entry['lot'],'message':str(e)})
        report['samples'].append(entry)
except Exception as e:report['errors'].append({'stage':'inventory','message':str(e)})
report['passed']=len(report['samples'])==5 and all(x.get('ok') for x in report['samples']) and not report['errors']
report['publish_performed']=False
Path('lennar_photo_test.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
if not report['passed']:sys.exit(1)
