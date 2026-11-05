import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('benchmark_grading', ROOT / 'grading' / 'grade.py')
grading = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grading)


class GradingTests(unittest.TestCase):
    def setUp(self):
        self.packet = next(grading.prepare([{'id': 'P01-CASE-001/d03', 'answer': '示例回答'}]))
        self.review = {'id': self.packet['id'], 'answer_sha256': self.packet['answer_sha256'],
                       'rubric_sha256': self.packet['rubric_sha256'], 'required': [True, True],
                       **{k: False for k in grading.FLAGS}, **{k: [] for k in grading.LISTS},
                       'reason': '示例判断'}

    def run_score(self, review=None, packet=None):
        p, r = packet or self.packet, review or self.review
        return list(grading.score({p['id']: p}, {r['id']: r}))[0]

    def test_rule_boundaries(self):
        self.assertTrue(self.run_score()['pass'])
        self.assertFalse(self.run_score({**self.review, 'required': [True, False]})['pass'])
        self.assertFalse(self.run_score({**self.review, '错认': True})['pass'])
        self.assertFalse(self.run_score({**self.review, '未知当事实': ['编造']})['pass'])
        self.assertTrue(self.run_score({**self.review, '无关旧事': ['甲', '乙']})['pass'])
        self.assertFalse(self.run_score({**self.review, '无关旧事': ['甲', '乙', '丙']})['pass'])
        self.assertFalse(self.run_score({**self.review, '不当私事披露': True})['pass'])

    def test_bad_review_and_modified_answer_are_rejected(self):
        for changed in ({'required': [True]}, {'错认': 'false'}, {'违反禁止': '无'}, {'reason': ''}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.run_score({**self.review, **changed})
        with self.assertRaises(ValueError):
            self.run_score(packet={**self.packet, 'answer': '被修改的回答'})
        with self.assertRaises(ValueError):
            list(grading.score({self.packet['id']: self.packet}, {}))
        with self.assertRaises(ValueError):
            grading.indexed([self.review, self.review])

    def test_all_evidence_is_from_public_history_before_cutoff(self):
        questions = grading.indexed(grading.read_rows(grading.DATA / 'exam-inputs.jsonl'))
        evidence = grading.indexed(grading.read_rows(ROOT / 'grading' / 'evidence.jsonl'))
        self.assertEqual(set(questions), set(evidence))
        histories = {}
        for ident, row in evidence.items():
            q = questions[ident]
            if q['persona'] not in histories:
                histories[q['persona']] = {x['轮次']: x for x in grading.read_rows(grading.DATA / q['history_file'])}
            history = histories[q['persona']]
            for source in row['sources']:
                self.assertLessEqual(source['turn'], q['cutoff_turn'])
                turn = history[source['turn']]
                self.assertEqual(source['time'], turn['逻辑时间'])
                field = '用户消息' if source['speaker'] == 'user' else '助手回复'
                self.assertIn(source['quote'], turn[field])

    def test_summary_uses_only_scored_questions(self):
        report = grading.summarize([self.run_score()])
        self.assertEqual((report['passed'], report['scored'], report['dataset_questions']), (1, 1, 714))
        self.assertEqual(report['groups']['persona']['P01']['total'], 1)


if __name__ == '__main__':
    unittest.main()
