from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

EVIDENCE_CLASSES={
 'SCRIPT_EXPLICIT','SCRIPT_NECESSARY_INFERENCE','VISUAL_CANON_LOCKED','USER_DIRECTED',
 'STRONG_INFERENCE','WEAK_INFERENCE','PROPOSED_NOT_CANON','UNSUPPORTED'
}

def load_json(path: str|Path) -> Any:
    p=Path(path)
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except FileNotFoundError as e:
        raise SystemExit(f'File not found: {p}') from e
    except json.JSONDecodeError as e:
        raise SystemExit(f'Invalid JSON in {p}: {e}') from e

def save_json(path: str|Path, data: Any) -> None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def stable_hash(data: Any) -> str:
    raw=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def bullet(items: list[str], prefix='- ') -> str:
    return '\n'.join(prefix+str(x) for x in items) if items else prefix+'None established.'
