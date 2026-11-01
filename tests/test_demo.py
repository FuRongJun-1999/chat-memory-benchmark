import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from datetime import timedelta

from demo import read_exam


ROOT = Path(__file__).resolve().parents[1] / 'demo'


class DemoIntegrityTests(unittest.TestCase):
    def test_every_manifest_file(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
        for name, digest in manifest['file_sha256'].items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256(read_exam.contained(ROOT, name).read_bytes()).hexdigest(), digest)

    def test_all_inputs_have_only_allowed_prefix(self):
        questions, histories = read_exam.load(ROOT)
        self.assertEqual(len(questions), 108)
        self.assertEqual(len(histories), 1)
        for q in questions:
            with self.subTest(question=q['id']):
                item = read_exam.get_question(q['id'], ROOT)
                self.assertEqual(set(item), {'id', 'persona', 'history_file', 'history_sha256',
                                            'now', 'cutoff_turn', 'question', 'history'})
                rows, times, _ = histories[q['history_file']]
                cutoff = q['cutoff_turn']
                self.assertEqual(item['history'], rows[:cutoff])
                self.assertLessEqual(times[cutoff - 1], read_exam.timestamp(q['now']))
                if cutoff < len(rows):
                    self.assertGreater(times[cutoff], read_exam.timestamp(q['now']))

    def test_answers_and_time_anchors_are_consistent(self):
        questions, _ = read_exam.load(ROOT)
        by_id = {q['id']: q for q in questions}
        keys = read_exam.jsonl(ROOT / 'review-only/answer-key.jsonl')
        cases = read_exam.jsonl(ROOT / 'review-only/cases-PUB01.jsonl')
        history = read_exam.jsonl(ROOT / 'histories/PUB01.jsonl')
        self.assertEqual(len(history), 360)
        self.assertEqual(len(cases), 27)
        self.assertEqual(len(keys), len(by_id))
        self.assertEqual({k['id'] for k in keys}, set(by_id))
        groups = {}
        for key in keys:
            q = by_id[key['id']]
            expected = timedelta(seconds=1) if key['interval_days'] == 0 else timedelta(days=key['interval_days'])
            now = read_exam.timestamp(q['now'])
            latest = max(read_exam.timestamp(a['time']) for a in key['anchors'])
            self.assertEqual(now - latest, expected)
            self.assertEqual(key['group_age_seconds'], expected.total_seconds())
            self.assertEqual(key['reference_answer_kind'], 'authored_example_not_system_output')
            groups.setdefault(key['case_id'], set()).add(key['interval_days'])
            for anchor in key['anchors']:
                self.assertLessEqual(anchor['last_turn'], q['cutoff_turn'])
                self.assertEqual(anchor['time'], history[anchor['last_turn'] - 1]['逻辑时间'])
                self.assertEqual(anchor['age_seconds'], (now - read_exam.timestamp(anchor['time'])).total_seconds())
        self.assertEqual(len(groups), 27)
        self.assertTrue(all(days == {0, 3, 15, 45} for days in groups.values()))
        for case in cases:
            for fact in case['facts']:
                for evidence in fact['evidence']:
                    field = {'user': '用户消息', 'assistant': '助手回复'}[evidence['speaker']]
                    self.assertIn(evidence['quote'], history[evidence['turn'] - 1][field])

    def test_corrupted_input_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / 'demo'
            shutil.copytree(ROOT, copy)
            with (copy / 'exam-inputs.jsonl').open('a', encoding='utf-8') as stream:
                stream.write('\n')
            with self.assertRaisesRegex(ValueError, 'SHA'):
                read_exam.load(copy)

    def test_future_history_rejected_even_with_updated_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / 'demo'
            shutil.copytree(ROOT, copy)
            questions = read_exam.jsonl(copy / 'exam-inputs.jsonl')
            questions[0]['cutoff_turn'] += 1
            path = copy / 'exam-inputs.jsonl'
            path.write_text('\n'.join(json.dumps(q, ensure_ascii=False) for q in questions) + '\n', encoding='utf-8')
            manifest = json.loads((copy / 'manifest.json').read_text(encoding='utf-8'))
            manifest['file_sha256']['exam-inputs.jsonl'] = hashlib.sha256(path.read_bytes()).hexdigest()
            (copy / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'cutoff'):
                read_exam.load(copy)

    def test_paths_and_unknown_ids_rejected(self):
        with self.assertRaises(ValueError):
            read_exam.contained(ROOT, '../outside.jsonl')
        with self.assertRaisesRegex(ValueError, 'Unknown question'):
            read_exam.get_question('PUB01-NOT-A-QUESTION', ROOT)


if __name__ == '__main__':
    unittest.main()
