import re
import json
import unittest
from pathlib import Path

from grading import grade


class Neo4jAuthorSubmissionTest(unittest.TestCase):
    def test_report_matches_answers_and_partial_review(self):
        root=Path(__file__).resolve().parents[1]
        result=root/'results'
        prefix='2026-11-05-dsh-neo4j-'
        answers=grade.indexed(grade.read_rows(result/(prefix+'answers.jsonl')))
        packets=grade.indexed(list(grade.prepare(answers.values())))
        reviews=grade.indexed(grade.read_rows(result/(prefix+'reviews.jsonl')))
        judged=list(grade.score(packets,reviews))
        self.assertEqual((len(judged),sum(x['pass'] for x in judged)),(714,682))
        manual=grade.indexed(grade.read_rows(result/(prefix+'manual-review.jsonl')))
        self.assertEqual(len(manual),28)
        for ident,row in manual.items():
            self.assertIn(ident,packets)
            self.assertIs(type(row['manual_pass']),bool)
            for field in ('answer_sha256','rubric_sha256'):
                if field in row:self.assertEqual(row[field],packets[ident][field])
        corrected=[{**row,'pass':manual.get(row['id'],{}).get('manual_pass',row['pass'])} for row in judged]
        report=grade.summarize(corrected)
        self.assertEqual(report['passed'],684)
        saved=json.loads((result/(prefix+'reviewed-summary.json')).read_text(encoding='utf-8'))
        self.assertEqual({k:saved[k] for k in ('passed','scored','dataset_questions','groups')},report)
        text=(result/'2026-11-05-dsh-neo4j.md').read_text(encoding='utf-8')
        for label,counts in report['groups']['content_tags'].items():
            pattern=rf'^\| {re.escape(label)} \| \d+ / {counts["total"]} \| {counts["passed"]} / {counts["total"]} \|$'
            self.assertRegex(text,re.compile(pattern,re.MULTILINE))
        for days,counts in report['groups']['interval_days'].items():
            pattern=rf'^\| {days} 天 \| \d+ / {counts["total"]} \| {counts["passed"]} / {counts["total"]} \|$'
            self.assertRegex(text,re.compile(pattern,re.MULTILINE))


if __name__=='__main__':unittest.main()
