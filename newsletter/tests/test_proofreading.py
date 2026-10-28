"""Targeted regressions for stat units and transaction sentence punctuation."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import build
import fetch_week


class ProofreadingTests(unittest.TestCase):
    def test_defensive_sack_units(self):
        for count,label in [(1,'1 sack'),(1.0,'1 sack'),(2,'2 sacks')]:
            with self.subTest(count=count):
                line=fetch_week.stat_line('DEF',{'gp':1,'sack':count})
                self.assertTrue(line.endswith(label))

    def test_dropped_player_suffix_already_closes_sentence(self):
        issue=json.loads((ROOT/'examples/2026-week7-regular/issue.json').read_text(encoding='utf-8'))
        names=['Pierre Strong Jr.','Michael Pittman Jr.','Brian Robinson Jr.','Rico Dowdle']
        row=issue['transactions']['free_agents'][0]
        issue['transactions']['free_agents']=[{**row,'drop':name} for name in names]
        original=copy.deepcopy(issue)
        html=build.render(build.derive(issue))
        for name in names:
            ending='' if name.endswith('.') else '.'
            self.assertIn('dropped '+name+ending+' <span',html)
        self.assertNotIn('Jr..',html)
        self.assertEqual(issue,original)

    def test_saved_example_values_are_proofread_without_changing_compounds(self):
        issue=json.loads((ROOT/'examples/2026-week7-regular/issue.json').read_text(encoding='utf-8'))
        self.assertIn('scored minus two in',issue['rankings'][0]['take'])
        self.assertIn('for minus three yards',issue['rankings'][5]['take'])
        self.assertIn('replacing minus one requires',issue['transactions']['waivers'][4]['note'])
        self.assertIn('zero-dollar',issue['transactions']['waivers'][4]['note'])
        self.assertEqual(issue['standouts'][5]['line'],'3 pts allowed, 213 yds allowed, 1 sack, 1 INT')


if __name__=='__main__':unittest.main()
