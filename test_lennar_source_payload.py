import json
from lennar_source_payload import parse_source_state

def page(state):
    return '<script id="__NEXT_DATA__" type="application/json">'+json.dumps({"props":{"pageProps":{"initialApolloState":state}}})+'</script>'

for label,html in [
    ("empty",""),("missing script","<html>Unavailable</html>"),
    ("broken JSON",'<script id="__NEXT_DATA__">{</script>'),
    ("missing state",'<script id="__NEXT_DATA__">{}</script>'),
    ("empty state",page({})),("wrong type",page([])),
    ("unrelated state",page({"x":{"__typename":"Other"}}))]:
    try:
        parse_source_state(html)
    except (ValueError,KeyError,TypeError):
        print("PASS rejected "+label)
    else:
        raise AssertionError("Accepted "+label)
for kind in ("CommunityType","HomesiteType"):
    state={"x":{"__typename":kind}}
    assert parse_source_state(page(state))==state
    print("PASS accepted "+kind)
