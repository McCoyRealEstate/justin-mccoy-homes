"""Offline regression of actual phase-6 candidate reconciliation."""
import hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
SCRIPT=Path(__file__).with_name('lennar_phase6_dry_run.py')
LOT='11166720149'
def home(lot,price=400000):
    return dict(lot=lot,cm='c0',s='M',p=price,a='Test address')
def html(homes):
    vals=dict(D=dict(h=homes,c=[dict(id='c'+str(i)) for i in range(20)]),LU={h['lot']:h['lot'] for h in homes},PH=[],HIMG={},PLANPH={},IMG={},IMPORTED='',UPDATED='')
    return '\n'.join('const '+k+' = '+json.dumps(v)+';' for k,v in vals.items())+'\nif (h.s === "S" || h.s === "C") h.np = 1'
def run(old,new,missing,classification,runid):
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp); out=p/'lennar_preview';out.mkdir();(p/'data').mkdir()
        shutil.copy(SCRIPT,p/SCRIPT.name)
        baseline=html(old)
        (p/'index.html').write_text(baseline)
        (out/'index-normalized-unpublished.html').write_text(html(new))
        (p/'data/inventory-freshness.json').write_text(json.dumps(dict(refresh_run_id=runid)))
        (out/'preview-report.json').write_text(json.dumps(dict(passed=True,result=dict(publish_performed=False,original_sha256=hashlib.sha256(baseline.encode()).hexdigest(),missing_existing_retained=missing))))
        (out/'verification-report.json').write_text(json.dumps(dict(passed=True,listings=[dict(lot=k,classification=classification,http_status=200,redirected=True,matching_homesite_objects=0,final_path_matches_lot=False) for k in missing])))
        subprocess.run([sys.executable,str(p/SCRIPT.name)],check=True,capture_output=True,text=True)
        assert (p/'index.html').read_text()==baseline
        report=json.loads((out/'phase6-publish-diff.json').read_text())
        result=json.JSONDecoder().raw_decode((out/'index-phase6-unpublished.html').read_text().split('const D = ',1)[1])[0]['h']
        return report,result
base=[home('fixture'+str(i)) for i in range(101)]
old=base+[home(LOT)]
r,sold=run(old,old,[LOT],'fetch_error','46075224473')
assert len(sold)==101 and r['removed'][0]['lot']==LOT
print('PASS operator confirmed sale')
returned=sold+[dict(home(LOT,425000),a='Updated address')]
r,active=run(sold,returned,[],'','later')
assert r['added'][0]['lot']==LOT and active[-1]['p']==425000 and active[-1]['a']=='Updated address'
print('PASS returned candidate with fresh price and address')
r,held=run(active,active,[LOT],'fetch_error','later')
assert held==active and r['held_removals'][0]['lot']==LOT
print('PASS later source failure retains listing')
r,resold=run(held,held,[LOT],'lot_not_in_page_data','later')
assert resold==base and r['removed'][0]['lot']==LOT
print('PASS verified resale after recovery')
r,again=run(resold,resold+[home(LOT,410000)],[],'','later')
assert again[-1]['p']==410000 and len({h['lot'] for h in again})==len(again)
print('PASS second return without duplicates')
