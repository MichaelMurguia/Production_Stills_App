from __future__ import annotations
import argparse, json
from common import load_json
from validate_spec import validate

def audit(spec: dict) -> dict:
    findings=[]
    for e in validate(spec): findings.append({'severity':'FAIL','type':'VALIDATION','message':e})
    forbidden={x.casefold() for x in spec.get('forbidden_elements',[])}
    for p in spec.get('panels',[]):
        overlap=forbidden & {x.casefold() for x in p.get('required_objects',[])}
        for x in sorted(overlap): findings.append({'severity':'FAIL','type':'CONTRADICTION','message':f"{p.get('id')}: required object is globally forbidden: {x}"})
    purposes=[p.get('purpose','').strip().casefold() for p in spec.get('panels',[])]
    if len(purposes)!=len(set(purposes)): findings.append({'severity':'WARN','type':'REPETITION','message':'Two or more panels have identical purposes'})
    held=[r for r in spec.get('evidence_ledger',[]) if r.get('status')=='HOLD']
    if held: findings.append({'severity':'FAIL','type':'UNRESOLVED_EVIDENCE','message':f'{len(held)} evidence rows remain HOLD'})
    decision='FAIL' if any(f['severity']=='FAIL' for f in findings) else ('PASS_WITH_WARNINGS' if findings else 'PASS')
    return {'specification_id':spec.get('specification_id'),'decision':decision,'findings':findings}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('--json',action='store_true')
    a=ap.parse_args(); report=audit(load_json(a.spec))
    if a.json: print(json.dumps(report,indent=2))
    else:
        print(report['decision'])
        for f in report['findings']: print(f"- [{f['severity']}] {f['type']}: {f['message']}")
    raise SystemExit(1 if report['decision']=='FAIL' else 0)
if __name__=='__main__': main()
