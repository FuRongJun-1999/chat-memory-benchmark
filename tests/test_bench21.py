import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmark-2.1' / 'harness'))

from bench21 import scoring  # noqa: E402
from bench21 import gateway  # noqa: E402
from bench21.systems import Bm25Local, FullContext, IncBM25  # noqa: E402
from bench21.runner import build_sentinel  # noqa: E402


def turn(n, user='你好', assistant='嗯'):
    return {'turn': n, 'time': f'2026-09-01T{(n % 24):02d}:00:00+08:00', 'user': user, 'assistant': assistant}


class ScoringTests(unittest.TestCase):
    def test_pass_rule(self):
        ok = {'required': ['met', 'met'], 'forbidden_hit': [], 'tempting_hit': [], 'unknown_asserted': []}
        self.assertTrue(scoring.judge_pass(ok))
        self.assertFalse(scoring.judge_pass({**ok, 'required': ['met', 'partial']}))
        self.assertFalse(scoring.judge_pass({**ok, 'forbidden_hit': [0]}))
        self.assertFalse(scoring.judge_pass({**ok, 'date_wrong': True}))
        self.assertFalse(scoring.judge_pass({**ok, 'over_hedged': True}))
        self.assertFalse(scoring.judge_pass({'required': []}))

    def test_weights_follow_traffic_shares(self):
        items = [{'id': 'a', 'group_age_seconds': 60}, {'id': 'b', 'group_age_seconds': 60},
                 {'id': 'c', 'group_age_seconds': 40 * 86400}]
        w = scoring.weights(items)
        self.assertAlmostEqual(w['a'] + w['b'], 0.54 / 0.55, places=6)     # only two bins present: shares renormalised
        self.assertAlmostEqual(sum(w.values()), 1.0, places=6)
        self.assertAlmostEqual(w['a'], w['b'])

    def test_severe_counts_double(self):
        items = [{'id': 'a', 'group_age_seconds': 60, 'rubric': {'severity': 'severe'}}, {'id': 'b', 'group_age_seconds': 60}]
        w = scoring.weights(items)
        self.assertAlmostEqual(w['a'], 2 * w['b'])

    def test_weighted_rate(self):
        items = [{'id': 'a', 'group_age_seconds': 60}, {'id': 'c', 'group_age_seconds': 40 * 86400}]
        self.assertAlmostEqual(scoring.weighted_rate(items, {'a': True, 'c': False}), 100 * 0.54 / 0.55, places=4)

    def test_composite_and_floor(self):
        self.assertAlmostEqual(scoring.composite(50, 10, 10), 50)
        self.assertAlmostEqual(scoring.composite(50, 20, 10), 47)           # double the cost: -3
        self.assertAlmostEqual(scoring.composite(50, 5, 10), 53)            # half the cost: +3
        self.assertAlmostEqual(scoring.composite(50, 0, 10), 56)            # floor at C_ref/4: at most +6

    def test_paired_rate(self):
        items = [{'id': 'a', 'twin_id': 't'}, {'id': 'b', 'twin_id': 't'}, {'id': 'c', 'twin_id': 'u'}, {'id': 'd', 'twin_id': 'u'}]
        rate, n = scoring.paired_rate(items, {'a': True, 'b': True, 'c': True, 'd': False})
        self.assertEqual((rate, n), (50.0, 2))


class GatewayTests(unittest.TestCase):
    def test_price_table(self):
        self.assertAlmostEqual(gateway.price_cny('deepseek-v4.1-flash', 1_000_000, 0), gateway.PRICES['models']['deepseek-v4.1-flash']['in_per_mtok'])
        self.assertEqual(gateway._priced('local:qwen3-8b'), 'deepseek-v4.1-flash')   # local models are priced as flash


class IsolationTests(unittest.TestCase):
    def test_bm25_only_knows_what_it_was_fed(self):
        bm = IncBM25()
        for t in (turn(1, '喜欢猫'), turn(2, '喜欢狗')):
            bm.add(t['user'] + t['assistant'])
        self.assertEqual(len(bm.dl), 2)
        self.assertEqual(bm.top('汤团', 5), [])               # a word that has not been said yet matches nothing

    def test_retrieval_never_shows_future_turns(self):
        s = Bm25Local()
        history = [turn(i, f'第{i}轮 话题{i % 3}') for i in range(1, 30)]
        for t in history[:20]:
            s.ingest(t)
        r = s.retrieve('第25轮 话题1', '2026-09-02T10:00:00+08:00', 20)
        self.assertTrue(r.used_turns and max(r.used_turns) <= 20)

    def test_full_context_keeps_the_most_recent_turns(self):
        s = FullContext(window_tokens=400)
        for i in range(1, 200):
            s.ingest(turn(i, '甲' * 40, '乙' * 40))
        r = s.retrieve('?', '2026-09-02T10:00:00+08:00', 199)
        self.assertEqual(r.used_turns[-1], 199)
        self.assertLess(len(r.used_turns), 199)

    def test_sentinel_canary_sits_after_the_cutoff(self):
        hist = {'M01': [{'turn': i, 'time': '2026-09-01T00:00:00+08:00', 'user': f'u{i}', 'assistant': f'a{i}'} for i in range(1, 101)]}
        items = [{'id': f'M01-G{i:03d}/d000', 'persona': 'M01', 'kind': 'main', 'cutoff_turn': 10 * i, 'question': f'问题{i}'} for i in range(1, 6)]
        hist2, canaries = build_sentinel(items, hist, 3, seed=1)
        self.assertEqual(len(canaries), 3)
        for c in canaries:
            self.assertEqual(c['canary_turn'], c['cutoff_turn'] + 1)
            self.assertIn(c['nonce'], hist2['M01'][c['canary_turn'] - 1]['user'])
        self.assertEqual(hist['M01'][0]['user'], 'u1')           # the input history is not modified


class DatasetTests(unittest.TestCase):
    def test_public_dataset_is_consistent(self):
        d = ROOT / 'benchmark-2.1' / 'dataset'
        man = json.loads((d / 'manifest.json').read_text(encoding='utf-8'))
        exam = [json.loads(x) for x in (d / 'exam-inputs.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
        key = {json.loads(x)['id']: json.loads(x) for x in (d / 'review-only' / 'answer-key.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()}
        self.assertEqual({e['id'] for e in exam}, set(key))
        self.assertTrue(all(key[e['id']]['split'] == 'dev' for e in exam))
        commit = json.loads((d / 'sealed-commitment.json').read_text(encoding='utf-8'))
        self.assertEqual(len(commit['sealed_exam_inputs_sha256']), 64)
        self.assertEqual(sorted(man['personas']), ['M01', 'M02'])


if __name__ == '__main__':
    unittest.main()
