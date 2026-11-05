import json
import unittest
from pathlib import Path


class SuzuForcedSummaryTests(unittest.TestCase):
    def test_coverage_and_reused_qwen(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / 'results/2026-11-05-suzu-forced-summary.json').read_text(encoding='utf-8'))
        previous = json.loads((root / 'results/2026-11-04-summary.json').read_text(encoding='utf-8'))
        self.assertEqual(data['question_set_sha256'], previous['question_set_sha256'])
        self.assertEqual(data['systems']['qwen-rag'], previous['systems']['qwen-rag'])
        suzu = data['systems']['suzu-native-forced']
        self.assertEqual(suzu['overall'], {'passed': 621, 'total': 714})
        self.assertEqual(sum(v['total'] for v in suzu['intervals'].values()), 714)
        self.assertEqual(sum(v['whole_answer_passed'] for v in suzu['intervals'].values()), 621)
        self.assertEqual(suzu['retrieval']['searches_per_question'], 1)
        self.assertEqual(suzu['retrieval']['limit'], 10)
        self.assertEqual(len(suzu['topics']), 27)
        for name, topic in suzu['topics'].items():
            self.assertEqual(sum(cell['total'] for cell in topic['cells']), topic['total'])
            self.assertEqual(sum(cell['whole_answer_passed'] for cell in topic['cells']), topic['whole_answer_passed'])
            qwen = data['systems']['qwen-rag']['topics'][name]
            self.assertEqual([c['total'] for c in topic['cells']], [c['total'] for c in qwen['cells']])
        self.assertEqual(len(list((root / 'charts/2026-11-05-suzu-forced').glob('*.png'))), 7)


if __name__ == '__main__':
    unittest.main()
