import json
import unittest
from pathlib import Path


class RetestSummaryTests(unittest.TestCase):
    def test_comparable_coverage_and_retained_qwen(self):
        root = Path(__file__).resolve().parents[1] / 'results'
        data = json.loads((root / '2026-11-04-summary.json').read_text(encoding='utf-8'))
        old = json.loads((root / '2026-11-01-first-four-summary.json').read_text(encoding='utf-8'))
        systems = data['systems']
        self.assertEqual(data['question_set_sha256'], old['question_set_sha256'])
        self.assertEqual(systems['qwen-rag']['topics'], old['systems']['qwen-rag']['topics'])
        for system in systems.values():
            self.assertEqual(system['overall']['total'], 714)
            self.assertEqual(sum(c['total'] for c in system['intervals'].values()), 714)
            self.assertEqual(sum(c['whole_answer_passed'] for c in system['intervals'].values()), system['overall']['passed'])
            self.assertEqual(len(system['topics']), 27)
            for topic in system['topics'].values():
                self.assertEqual(sum(c['total'] for c in topic['cells']), topic['total'])
                self.assertEqual(sum(c['whole_answer_passed'] for c in topic['cells']), topic['whole_answer_passed'])


if __name__ == '__main__':
    unittest.main()
