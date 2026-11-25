"""Render a read-only offline dashboard from the command center report."""
import json
from pathlib import Path
from html import escape
r=json.loads(Path('command-center.json').read_text())
def e(v): return escape(str(v if v is not None else 'Unavailable'))
def metric(label,value): return '<article><small>'+e(label)+'</small><strong>'+e(value)+'</strong></article>'
def table(rows): return '<table>'+''.join('<tr><th>'+e(k)+'</th><td>'+e(v)+'</td></tr>' for k,v in rows)+'</table>'
p=r.get('playback_evidence') or {}
c=r.get('inventory_changes') or {}
metrics=[('Homes',r.get('homes')),('Directory communities',r.get('directory_communities')),('Communities with inventory',r.get('communities_with_inventory')),('Unique tour links',r.get('unique_tour_urls')),('Inventory verification',r.get('freshness_status')),('Source errors',len(r.get('source_errors',{})))]
body='<header><small>JUS3D / OPERATIONS</small><h1>Media Command Center</h1><p>Snapshot: '+e(r.get('generated_at'))+' · Read-only historical report</p></header><main><section class="metrics">'+''.join(metric(k,v) for k,v in metrics)+'</section>'
body+='<section><h2>Virtual tour evidence</h2><p>Historical observations are not guarantees of current playback.</p>'+table([('Evidence status',p.get('status')),('Latest observation',p.get('latest_observation')),('Matched URLs',p.get('matched_urls')),('Unchecked URLs',p.get('unchecked_current_urls'))])+table(list((p.get('combined') or {}).items()))+'</section>'
body+='<section><h2>Inventory activity</h2>'+table([('Comparison status',c.get('status')),('Baseline',c.get('baseline_at')),('Added',len(c['added']) if 'added' in c else None),('Removed from feed — not confirmed sold',len(c['removed_from_feed_not_confirmed_sold']) if 'removed_from_feed_not_confirmed_sold' in c else None),('Changed',len(c['changed']) if 'changed' in c else None)])+'</section>'
for title,key in [('Held removals','held_removals'),('Missing tour links','missing_tour_homes'),('Missing amenities','missing_amenity_homes'),('Photography provenance','photo_provenance'),('Source errors','source_errors'),('Inventory change details','inventory_changes')]:
    body+='<details><summary>'+e(title)+'</summary><pre>'+e(json.dumps(r.get(key),indent=2))+'</pre></details>'
body+='</main>'
Path('command-center.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jus3D Media Command Center</title><style>*{box-sizing:border-box}body{margin:0;background:#f5f6f8;color:#10243b;font:16px system-ui}header{background:#10243b;color:white;padding:32px max(20px,calc((100vw - 1100px)/2))}header small{color:#e3c38b;letter-spacing:.15em}h1{margin:8px 0}main{max-width:1100px;margin:auto;padding:20px}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px}article,section:not(.metrics),details{background:white;border:1px solid #dce2e9;border-radius:10px;padding:18px;margin-bottom:14px}article strong{display:block;font-size:24px;margin-top:8px}small{color:#536579}header small{color:#e3c38b}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #e5e9ef;overflow-wrap:anywhere}th{font-weight:500}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer;font-weight:650}</style>'+body+'</html>',encoding='utf-8')
