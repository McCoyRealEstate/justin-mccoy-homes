#!/usr/bin/env python3
"""Read-only SEO metadata audit for the published homepage."""
from pathlib import Path
from html.parser import HTMLParser
import json

class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_head=False; self.in_title=False; self.title=""; self.meta=[]; self.links=[]; self.jsonld=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=="head": self.in_head=True
        if not self.in_head: return
        if tag=="title": self.in_title=True
        if tag=="meta": self.meta.append(a)
        if tag=="link": self.links.append(a)
        if tag=="script" and a.get("type")=="application/ld+json": self.jsonld+=1
    def handle_endtag(self, tag):
        if tag=="title": self.in_title=False
        if tag=="head": self.in_head=False
    def handle_data(self, data):
        if self.in_title: self.title+=data

p=HeadParser()
with Path("index.html").open(encoding="utf-8") as f:
    # Metadata is expected in the document head, before large inline image data.
    p.feed(f.read(150000))
def meta(name):
    return next((x.get("content","") for x in p.meta if x.get("name")==name or x.get("property")==name),"")
def link(rel):
    return next((x.get("href","") for x in p.links if rel in x.get("rel","").split()),"")
report={"title":p.title.strip(),"description":meta("description"),"robots":meta("robots"),
"canonical":link("canonical"),"og:title":meta("og:title"),"og:description":meta("og:description"),
"og:image":meta("og:image"),"twitter:card":meta("twitter:card"),
"favicon":link("icon"),"structured_data_blocks":p.jsonld}
print(json.dumps(report,indent=2))
