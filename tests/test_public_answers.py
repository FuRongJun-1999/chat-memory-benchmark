import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSWERS = ROOT / 'results' / 'answers'


class PublicAnswerTests(unittest.TestCase):
    def test_manifest_and_question_ids(self):
        key = ROOT / 'datasets/natural-timegrid-20261101-v2/review-only/answer-key.jsonl'
        ids = {json.loads(line)['id'] for line in key.read_text(encoding='utf8').splitlines() if line}
        self.assertEqual(len(ids), 714)
        manifest = json.loads((ANSWERS / 'manifest.json').read_text(encoding='utf8'))
        for item in manifest['systems']:
            with self.subTest(system=item['name']):
                raw = (ANSWERS / item['file']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'])
                rows = [json.loads(line) for line in raw.decode('utf8').splitlines() if line]
                self.assertEqual(len(rows), item['answers'])
                self.assertEqual(len(rows), len({row['id'] for row in rows}))
                self.assertTrue({row['id'] for row in rows} <= ids)
                for row in rows:
                    self.assertEqual(set(row), {'id', 'answer', 'answer_sha256'})
                    self.assertEqual(hashlib.sha256(row['answer'].encode('utf8')).hexdigest(), row['answer_sha256'])


if __name__ == '__main__':
    unittest.main()
