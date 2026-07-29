from __future__ import annotations
import argparse
from common import save_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('output'); ap.add_argument('--id',required=True); ap.add_argument('--subject',required=True); ap.add_argument('--mode',choices=['CANON_EXTRACTION','DESIGN_EXPLORATION'],default='CANON_EXTRACTION')
    a=ap.parse_args()
    spec={'specification_id':a.id,'project':'The Beltminers','subject':a.subject,'mode':a.mode,'status':'DRAFT','canon_sources':[{'id':'CURRENT_SCREENPLAY','type':'screenplay','status':'CURRENT'}],'forbidden_elements':[],'canon_budget':{'weak_inference_max':2 if a.mode=='CANON_EXTRACTION' else 10,'unsupported_max':0},'layout':{'canvas':'wide cinematic production board','panels':[{'id':'P01','allocation_percent':100}]},'panels':[{'id':'P01','purpose':'Define the primary production question','required_objects':['SUBJECT_TO_DEFINE'],'forbidden_objects':[],'evidence':['USER_DIRECTED'],'scale':'WIDE','composition_role':'hero'}],'evidence_ledger':[{'object_id':'OBJ-001','panel_id':'P01','object':'SUBJECT_TO_DEFINE','evidence_class':'USER_DIRECTED','source':'user request','confidence':1.0,'status':'PASS','rationale':'placeholder; replace before approval'}]}
    save_json(a.output,spec); print(f'CREATED {a.output}')
if __name__=='__main__': main()
