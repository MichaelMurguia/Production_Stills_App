from __future__ import annotations
import argparse, zipfile
from pathlib import Path

def main():
    root=Path(__file__).resolve().parents[1]
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default=str(root.parent/(root.name+'_source.zip'))); a=ap.parse_args()
    out=Path(a.output)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p!=out:
                z.write(p,p.relative_to(root.parent))
    print(out)
if __name__=='__main__': main()
