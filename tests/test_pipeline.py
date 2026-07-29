import json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_spec import validate
from compile_prompt import compile_prompt
from audit_spec import audit

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.valid=json.loads((ROOT/'examples/minimal_valid_spec.json').read_text())
    def test_valid_spec(self): self.assertEqual(validate(self.valid),[])
    def test_invalid_spec(self):
        bad=json.loads((ROOT/'examples/invalid_spec.json').read_text())
        self.assertTrue(validate(bad))
    def test_prompt_compiles(self):
        p=compile_prompt(self.valid)
        self.assertIn('CANDIDATE — UNAPPROVED',p)
        self.assertIn('SPEC HASH:',p)
        self.assertIn('animals',p)
    def test_audit_passes(self): self.assertEqual(audit(self.valid)['decision'],'PASS')
    def test_weak_budget(self):
        self.valid['canon_budget']['weak_inference_max']=0
        self.valid['evidence_ledger'][0]['evidence_class']='WEAK_INFERENCE'
        self.assertTrue(any('weak inference budget exceeded' in e for e in validate(self.valid)))

if __name__=='__main__': unittest.main()
