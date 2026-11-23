#!/usr/bin/env python3
"""Idempotently add McCoy Real Estate SEO tags to a generated homepage."""
import json,re,sys
from pathlib import Path
from html import escape
p=Path(sys.argv[1] if len(sys.argv)>1 else "index.html")
html=p.read_text(encoding="utf-8")
m=re.search(r"<head\b[^>]*>.*?</head\s*>",html,re.I|re.S)
if not m:raise SystemExit("Missing HTML head")
title="McCoy Real Estate | New Homes in Central Florida"
description="Explore Lennar new construction homes across Central Florida with Justin McCoy. Browse available homes, floor plans, pricing and communities."
url="https://jus3d.com/"
social=["https://www.facebook.com/JusRealtor","https://www.linkedin.com/in/justinmccoyrealtor","https://www.instagram.com/mccoyrealestate/"]
schema={"@context":"https://schema.org","@graph":[{"@type":"WebSite","@id":url+"#website","name":"McCoy Real Estate","url":url,"description":description},{"@type":"Person","@id":url+"#justin-mccoy","name":"Justin McCoy","jobTitle":"New Home Consultant","worksFor":{"@type":"Organization","name":"Lennar"},"url":url,"sameAs":social},{"@type":"WebPage","@id":url+"#webpage","name":title,"url":url,"description":description,"isPartOf":{"@id":url+"#website"},"about":{"@id":url+"#justin-mccoy"}}]}
def meta(attr,name,value):return '<meta '+attr+'="'+name+'" content="'+escape(value,quote=True)+'">'
tags=['<title>'+escape(title)+'</title>',meta('name','description',description),meta('name','robots','index, follow, max-image-preview:large'),'<link rel="canonical" href="'+url+'">','<link rel="icon" type="image/svg+xml" href="/favicon.svg">',meta('property','og:type','website'),meta('property','og:site_name','McCoy Real Estate'),meta('property','og:url',url),meta('property','og:title',title),meta('property','og:description',description),meta('property','og:image',url+'og-preview.png'),meta('property','og:image:width','1200'),meta('property','og:image:height','630'),meta('name','twitter:card','summary_large_image'),meta('name','twitter:title',title),meta('name','twitter:description',description),meta('name','twitter:image',url+'og-preview.png'),'<script type="application/ld+json">'+json.dumps(schema,separators=(',',':'))+'</script>']
head=m.group()
head=re.sub(r'<!-- MCCOY_SEO_START -->.*?<!-- MCCOY_SEO_END -->','',head,flags=re.S)
head=re.sub(r'<title\b[^>]*>.*?</title\s*>','',head,flags=re.I|re.S)
head=re.sub(r'<meta\b[^>]*\b(?:name|property)\s*=\s*["\'](?:description|robots|og:[^"\']+|twitter:[^"\']+)["\'][^>]*>','',head,flags=re.I)
head=re.sub(r'<link\b[^>]*\brel\s*=\s*["\'](?:canonical|icon)["\'][^>]*>','',head,flags=re.I)
block='\n<!-- MCCOY_SEO_START -->\n'+'\n'.join(tags)+'\n<!-- MCCOY_SEO_END -->\n'
head=re.sub(r'</head\s*>',lambda _:block+'</head>',head,count=1,flags=re.I)
new=html[:m.start()]+head+html[m.end():]
p.write_text(new,encoding="utf-8")
print("SEO tags applied:",p)
