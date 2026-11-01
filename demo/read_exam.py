"""Read a public demonstration question and its allowed history, without answers."""
import argparse
import bisect
from datetime import datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def contained(root, name):
    candidate = (root / name).resolve()
    candidate.relative_to(root.resolve())
    return candidate


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Timestamp needs an explicit timezone')
    return result


def load(root=ROOT):
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    exams = contained(root, 'exam-inputs.jsonl')
    if hashlib.sha256(exams.read_bytes()).hexdigest() != manifest['file_sha256']['exam-inputs.jsonl']:
        raise ValueError('Exam file SHA differs from manifest')
    questions = jsonl(exams)
    if len({q['id'] for q in questions}) != len(questions):
        raise ValueError('Duplicate question IDs')
    histories = {}
    for q in questions:
        if set(q) != {'id', 'persona', 'history_file', 'history_sha256', 'now', 'cutoff_turn', 'question'}:
            raise ValueError('Exam input contains unexpected fields')
        name = q['history_file']
        if name not in histories:
            p = contained(root, name)
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            if digest != manifest['file_sha256'][name]:
                raise ValueError('History SHA differs from manifest')
            rows = jsonl(p)
            times = [timestamp(r['逻辑时间']) for r in rows]
            if any(a >= b for a, b in zip(times, times[1:])):
                raise ValueError('History times must increase strictly')
            if [r['轮次'] for r in rows] != list(range(1, len(rows) + 1)):
                raise ValueError('History turn sequence is broken')
            if any(set(r) != {'轮次', '逻辑时间', '用户消息', '助手回复', '日'} for r in rows):
                raise ValueError('History contains unexpected fields')
            histories[name] = (rows, times, digest)
        rows, times, digest = histories[name]
        if q['history_sha256'] != digest:
            raise ValueError('Question binds another history')
        cutoff = bisect.bisect_right(times, timestamp(q['now']))
        if cutoff != q['cutoff_turn'] or not 0 < cutoff <= len(rows):
            raise ValueError('Question cutoff includes future history or omits available turns')
    return questions, histories


def get_question(question_id, root=ROOT):
    questions, histories = load(root)
    q = next((q for q in questions if q['id'] == question_id), None)
    if q is None:
        raise ValueError('Unknown question ID: ' + question_id)
    return {**q, 'history': histories[q['history_file']][0][:q['cutoff_turn']]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', help='For example PUB01-C001/d45')
    group.add_argument('--verify-all', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.verify_all:
        questions, histories = load()
        result = {'status': 'verified', 'questions': len(questions), 'histories': len(histories),
                  'scope': 'SHA, input fields, chronology and exact cutoff; no model calls or grading'}
    else:
        result = get_question(args.id)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(serialized, encoding='utf-8')
    else:
        print(serialized, end='')
