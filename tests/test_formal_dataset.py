import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


class FormalDatasetTests(unittest.TestCase):
    def test_scored_dataset_and_reader(self):
        root = Path(__file__).resolve().parents[1] / 'datasets/natural-timegrid-20261101-v2'
        manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
        expected_source = '1d4026b58ac6fa02691960f54b16cc62308c34abd2d16bfe19d8a1fd6adb4b34'
        self.assertEqual(manifest['source_release_manifest_sha256'], expected_source)
        actual_files = {p.relative_to(root).as_posix() for p in root.rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts}
        self.assertEqual(actual_files, set(manifest['file_sha256']) | {'manifest.json'})
        for rel, expected in manifest['file_sha256'].items():
            self.assertEqual(hashlib.sha256((root / rel).read_bytes()).hexdigest(), expected)
        def read_rows(rel):
            return [json.loads(line) for line in (root / rel).read_text(encoding='utf-8').splitlines() if line.strip()]
        questions = read_rows('exam-inputs.jsonl')
        keys = read_rows('review-only/answer-key.jsonl')
        ids = {x['id'] for x in questions}
        self.assertEqual(len(questions), 714)
        self.assertEqual(len(ids), 714)
        self.assertEqual(ids, {x['id'] for x in keys})
        self.assertEqual(len(keys), 714)
        result = subprocess.run([sys.executable, str(root / 'read_exam.py'), '--verify-all'],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)['verified_inputs'], 714)


if __name__ == '__main__':
    unittest.main()
