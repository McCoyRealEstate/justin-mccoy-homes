"""Exercise the actual community generator without changing production inventory."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    root=pathlib.Path(tmp)
    shutil.copy(pathlib.Path(__file__).with_name('generate_community_pages.py'),root)
    (root/'data').mkdir()
    (root/'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')
    bridge={'id':'bridgewalk','community':'Bridgewalk','city':'St. Cloud'}
    nearby={'id':'waterlin','community':'Waterlin','city':'St. Cloud'}
    def home(c,lot):
        return {'community_id':c['id'],'community':c['community'],'lot':lot,'plan':'Example','price':400000,'sqft':2000,'availability':'Move-in ready'}
    def render(directory,homes):
        source=root/'data/inventory.json'
        source.write_text(json.dumps({'communities':directory,'homes':homes,'listings':[]}))
        subprocess.run([sys.executable,str(root/'generate_community_pages.py'),str(source)],check=True)
        return (root/'communities/bridgewalk.html').read_text()
    active=render([bridge,nearby],[home(bridge,'1'),home(nearby,'2')])
    assert 'Available Homes in Bridgewalk' in active and 'Still interested in Bridgewalk?' not in active
    empty=render([bridge,nearby],[home(nearby,'2')])
    assert 'Still interested in Bridgewalk?' in empty and 'Inquire About Future Availability' in empty
    assert 'href="/communities/waterlin.html"' in empty
    removed=render([nearby],[home(nearby,'2')])
    assert 'Still interested in Bridgewalk?' in removed and 'not currently listed in our active directory' in removed
    restored=render([bridge,nearby],[home(bridge,'3'),home(nearby,'2')])
    assert 'Available Homes in Bridgewalk' in restored and 'Still interested in Bridgewalk?' not in restored
    assert 'Homesite 3' in restored
    for page in (active,empty,removed,restored):
        assert '<h2>Buyer Services</h2>' not in page, 'Redundant buyer services section returned'
    print('Community lifecycle fixture passed: active, empty, removed, restored')
