import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ChartDataTests(unittest.TestCase):
    def test_shared_questions_and_frozen_four_system_totals(self):
        chart = json.loads((ROOT / 'charts/2026-11-01/data.json').read_text(encoding='utf-8'))
        frozen = json.loads((ROOT / 'results/2026-11-01-summary.json').read_text(encoding='utf-8'))
        self.assertEqual(chart['comparison_count'], 687)
        self.assertEqual(len(chart['systems']), 7)
        for key, old in frozen['systems'].items():
            current = chart['systems'][key]
            self.assertEqual(current['passed'], old['common']['passed'])
            self.assertEqual(current['total'], old['common']['total'])
            for topic, counts in current['topics'].items():
                self.assertEqual(counts['passed'], old['topics'][topic]['whole_answer_passed'])
                self.assertEqual(counts['total'], old['topics'][topic]['total'])

    def test_cost_formula_and_topic_denominators(self):
        chart = json.loads((ROOT / 'charts/2026-11-01/data.json').read_text(encoding='utf-8'))
        reference = chart['systems']['qwen-rag']
        for key, current in chart['systems'].items():
            c = current['cost']
            calculated = (c['prompt_tokens'] - c['cached_tokens'] + c['cached_tokens'] * .02 + c['completion_tokens'] * 4) / 1e6
            self.assertAlmostEqual(calculated, c['deepseek_cny'])
            self.assertAlmostEqual(sum(c['qwen_tokens_by_model'].values()) * .5 / 1e6, c['qwen_cny'])
            self.assertAlmostEqual(c['deepseek_cny'] + c['qwen_cny'], c['cny'])
            self.assertEqual(c['completed_answers'], current['full_answered'])
            self.assertEqual(len(current['topics']), 27)
            for topic, counts in current['topics'].items():
                cells = counts['cells']
                self.assertEqual(sum(x['passed'] for x in cells), counts['passed'])
                self.assertEqual(sum(x['total'] for x in cells), counts['total'])
                self.assertEqual([x['total'] for x in cells], [x['total'] for x in reference['topics'][topic]['cells']])
                self.assertTrue(all(0 <= x['passed'] <= x['total'] for x in cells))


if __name__ == '__main__':
    unittest.main()
