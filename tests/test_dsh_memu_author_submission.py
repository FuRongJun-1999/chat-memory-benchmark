import json
import re
import unittest
from pathlib import Path


class DshMemuAuthorSubmissionTest(unittest.TestCase):
    def test_report_matches_summary(self):
        root = Path(__file__).resolve().parents[1]
        result = root / 'results'
        prefix = '2026-11-06-dsh-memu-memory'
        saved = json.loads((result / (prefix + '-summary.json')).read_text(encoding='utf-8'))
        self.assertEqual(saved['dataset_questions'], 714)
        self.assertEqual((saved['passed'], saved['scored']), (653, 714))
        self.assertEqual(sum(x['passed'] for x in saved['groups']['persona'].values()), 653)
        text = (result / (prefix + '.md')).read_text(encoding='utf-8')
        self.assertRegex(text, re.compile(r'^\| DeepSeek 自动初判 \| 653 / 714 \| 91\.46% \|$', re.MULTILINE))
        for label, counts in saved['groups']['content_tags'].items():
            pattern = rf'^\| {re.escape(label)} \| {counts["passed"]} / {counts["total"]} \|$'
            self.assertRegex(text, re.compile(pattern, re.MULTILINE))
        for days, counts in saved['groups']['interval_days'].items():
            pattern = rf'^\| {days} 天 \| {counts["passed"]} / {counts["total"]} \|$'
            self.assertRegex(text, re.compile(pattern, re.MULTILINE))


if __name__ == '__main__':
    unittest.main()
