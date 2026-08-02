from __future__ import annotations
import argparse
from common import load_json, EVIDENCE_CLASSES

REQUIRED=['specification_id','project','subject','mode','status','canon_sources','forbidden_elements','canon_budget','layout','panels','evidence_ledger']

def validate(spec: dict) -> list[str]:
    errors=[]
    for k in REQUIRED:
        if k not in spec: errors.append(f'missing required field: {k}')
    # The rule is presence, not a hardcoded film (user-caught 2026-08-02:
    # specs now record the active production's name; the validator must
    # accept any non-empty project).
    if not str(spec.get('project','')).strip(): errors.append('project must be set')
    mode=spec.get('mode')
    if mode not in {'CANON_EXTRACTION','DESIGN_EXPLORATION'}: errors.append('invalid mode')
    if not spec.get('canon_sources'): errors.append('canon_sources must not be empty')
    budget=spec.get('canon_budget',{})
    if budget.get('unsupported_max')!=0: errors.append('unsupported_max must be 0')
    weak_max=budget.get('weak_inference_max')
    if not isinstance(weak_max,int) or weak_max<0: errors.append('weak_inference_max must be a nonnegative integer')
    panels=spec.get('panels',[])
    panel_ids=[p.get('id') for p in panels]
    if len(panel_ids)!=len(set(panel_ids)): errors.append('panel ids must be unique')
    alloc=sum(float(p.get('allocation_percent',0)) for p in spec.get('layout',{}).get('panels',[]))
    if not (99.0 <= alloc <= 101.0): errors.append(f'layout allocation must total 100, got {alloc:g}')
    weak=unsupported=0
    for i,row in enumerate(spec.get('evidence_ledger',[])):
        ec=row.get('evidence_class'); status=row.get('status')
        if ec not in EVIDENCE_CLASSES: errors.append(f'evidence_ledger[{i}] invalid evidence_class: {ec}')
        if row.get('panel_id') not in panel_ids: errors.append(f'evidence_ledger[{i}] references unknown panel')
        if not row.get('source','').strip(): errors.append(f'evidence_ledger[{i}] has no source')
        if ec=='WEAK_INFERENCE' and status=='PASS': weak+=1
        if ec=='UNSUPPORTED' and status=='PASS': unsupported+=1
        if status not in {'PASS','HOLD','REMOVE'}: errors.append(f'evidence_ledger[{i}] invalid status')
    if isinstance(weak_max,int) and weak>weak_max: errors.append(f'weak inference budget exceeded: {weak}>{weak_max}')
    if unsupported>0: errors.append(f'unsupported objects passed: {unsupported}')
    if mode=='CANON_EXTRACTION':
        proposed=sum(1 for r in spec.get('evidence_ledger',[]) if r.get('evidence_class')=='PROPOSED_NOT_CANON' and r.get('status')=='PASS')
        if proposed: errors.append('PROPOSED_NOT_CANON cannot pass in CANON_EXTRACTION mode')
    required_by_panel={p['id']:set(p.get('required_objects',[])) for p in panels if 'id' in p}
    passed={(r.get('panel_id'),r.get('object')) for r in spec.get('evidence_ledger',[]) if r.get('status')=='PASS'}
    for pid,objs in required_by_panel.items():
        for obj in objs:
            if (pid,obj) not in passed: errors.append(f'required object lacks PASS evidence row: {pid} / {obj}')
    return errors

def main():
    ap=argparse.ArgumentParser(description='Validate a Beltminers Production Generation Specification')
    ap.add_argument('spec'); args=ap.parse_args()
    errors=validate(load_json(args.spec))
    if errors:
        print('SPEC_FAIL')
        for e in errors: print(f'- {e}')
        raise SystemExit(1)
    print('SPEC_PASS')
if __name__=='__main__': main()
