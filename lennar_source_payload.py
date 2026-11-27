"""Reject malformed source payloads before inventory reconciliation."""
import json
from bs4 import BeautifulSoup

def parse_source_state(html):
    tag=BeautifulSoup(html,"html.parser").find("script",id="__NEXT_DATA__")
    if not tag or not tag.string:
        raise ValueError("Missing NEXT_DATA")
    state=json.loads(tag.string)["props"]["pageProps"]["initialApolloState"]
    if not isinstance(state,dict) or not state:
        raise ValueError("Empty or invalid Apollo state")
    if not any(isinstance(v,dict) and v.get("__typename") in {"CommunityType","HomesiteType"} for v in state.values()):
        raise ValueError("No recognizable inventory or community objects")
    return state
