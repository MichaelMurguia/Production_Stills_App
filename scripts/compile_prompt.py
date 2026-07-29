from __future__ import annotations
import argparse
from pathlib import Path
from common import load_json, bullet, stable_hash
from validate_spec import validate

def compile_prompt(spec: dict) -> str:
    errors=validate(spec)
    if errors: raise ValueError('Specification failed validation:\n'+'\n'.join('- '+e for e in errors))
    lines=[]
    lines += [f"BELTMINERS PRODUCTION RENDER INSTRUCTIONS",f"SPECIFICATION: {spec['specification_id']}",f"SPEC HASH: {stable_hash(spec)}",f"SUBJECT: {spec['subject']}",f"MODE: {spec['mode']}",'']
    lines += ['NON-NEGOTIABLE SOURCE RULES','Render only what the approved specification requires. Do not invent additional worldbuilding, objects, culture, technology, fauna, vehicles, symbols, characters, props, or action. Omit unspecified content rather than filling space. Master Board #001 controls presentation grammar only.','']
    lines += ['BOARD PRESENTATION',str(spec.get('render_intent','Wide painterly production-development board; image-first hierarchy; concise labels; visible brushwork; no glossy marketing finish.')),f"Canvas: {spec['layout'].get('canvas','wide cinematic')}",'']
    lines += ['FORBIDDEN ELEMENTS',bullet(spec.get('forbidden_elements',[])),'']
    for p in spec['panels']:
        lines += [f"PANEL {p['id']} — {p.get('title',p['purpose'])}",f"Purpose: {p['purpose']}",f"Required: {', '.join(p.get('required_objects',[])) or 'None'}",f"Forbidden: {', '.join(p.get('forbidden_objects',[])) or 'None'}",f"Evidence: {', '.join(p.get('evidence',[]))}",f"Scale: {p.get('scale','unspecified')}",f"Composition role: {p.get('composition_role','distinct production question')}",'']
    lines += ['PRESERVE','All approved asset identity, geometry, orientation, proportions, materials, layout hierarchy, and reference-role boundaries.','']
    lines += ['FINAL INSTRUCTION','The output is a CANDIDATE — UNAPPROVED. Do not add unsupported decorative content.']
    return '\n'.join(lines).rstrip()+'\n'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('--output','-o')
    a=ap.parse_args(); spec=load_json(a.spec)
    try: text=compile_prompt(spec)
    except ValueError as e: print(e); raise SystemExit(1)
    if a.output: Path(a.output).write_text(text,encoding='utf-8')
    else: print(text,end='')
if __name__=='__main__': main()
