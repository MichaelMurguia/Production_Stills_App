from __future__ import annotations
import argparse, datetime as dt
from pathlib import Path
from common import load_json, save_json
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'project_state/project_state.json'

def stamp(): return dt.datetime.now(dt.timezone.utc).isoformat()
def load(path): return load_json(path)
def save(path,s): s['updated_at']=stamp(); s['version']=int(s.get('version',0))+1; save_json(path,s)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--state',default=str(DEFAULT)); sub=ap.add_subparsers(dest='cmd',required=True)
    sub.add_parser('show')
    p=sub.add_parser('set-current'); p.add_argument('board_id')
    p=sub.add_parser('lock-asset'); p.add_argument('asset_id'); p.add_argument('--note',default='')
    p=sub.add_parser('approve-board'); p.add_argument('board_id'); p.add_argument('--scope',default='entire board')
    p=sub.add_parser('reject-board'); p.add_argument('board_id'); p.add_argument('--reason',required=True)
    p=sub.add_parser('prohibit'); p.add_argument('description')
    a=ap.parse_args(); path=Path(a.state); s=load(path)
    if a.cmd=='show':
        import json; print(json.dumps(s,indent=2)); return
    if a.cmd=='set-current': s.setdefault('active',{})['board_id']=a.board_id
    elif a.cmd=='lock-asset': s.setdefault('assets',{}).setdefault(a.asset_id,{}) .update({'status':'LOCKED','note':a.note,'updated_at':stamp()})
    elif a.cmd=='approve-board': s.setdefault('boards',{}).setdefault(a.board_id,{}) .update({'status':'APPROVED','scope':a.scope,'updated_at':stamp()})
    elif a.cmd=='reject-board': s.setdefault('boards',{}).setdefault(a.board_id,{}) .update({'status':'REJECTED','reason':a.reason,'updated_at':stamp()})
    elif a.cmd=='prohibit':
        arr=s.setdefault('prohibited_inventions',[])
        if a.description not in arr: arr.append(a.description)
    save(path,s); print(f'UPDATED {path}')
if __name__=='__main__': main()
