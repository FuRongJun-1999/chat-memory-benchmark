# -*- coding: utf-8 -*-
"""中文陪伴记忆 Benchmark 2.1 本地校验器（不联网，只用标准库）。版本 read-exam-v2.1（在 v2.0 基础上增加新题检查 N1–N6）

用法：
  python read_exam_v2.py                 基础检查（只需要 exam-inputs.jsonl、histories/、manifest.json；被测方也能跑）
  python read_exam_v2.py --verify-all    再加上 review-only 里的全部检查（出题方/复核方用）
  python read_exam_v2.py --root DIR      指定发布目录（默认是本文件所在目录）
  python read_exam_v2.py --json          输出机器可读的 JSON 摘要
  python read_exam_v2.py --load          只读取并返回题目（给程序 import 用：load_exam(root)）

基础检查（规格第 5 节“沿用”部分）
  B1 exam-inputs.jsonl 每行的键集合恰好是 {id, persona, history_file, history_sha256, now, cutoff_turn, question}（严格白名单，不许多也不许少）
  B2 id 唯一，格式合法（主题 Mxx-Gnnn/dNNN，对照题 Mxx-Knn）
  B3 persona 在 manifest 的人物白名单里；history_file 存在；其 SHA256 与 history_sha256、manifest 三者一致
  B4 历史文件：每行键为 {轮次, 逻辑时间, 用户消息, 助手回复, 日}（可选 会话），轮次从 1 连续，逻辑时间单调不减
  B5 now 带时区、可解析；cutoff_turn = 逻辑时间不晚于 now 的最后一轮
  B6 question 非空字符串
  B7 manifest 里每个文件的 SHA256 都与磁盘一致（manifest 自身除外）
--verify-all 新增（规格第 5 节“新增”部分）
  V1 exam-inputs 的每个 id 在 answer-key 里都有答案；answer-key 里除备用组外的 id 都在 exam-inputs 里；隔离区的 id 不在其中
  V2 锚点轮（每个事实最后一次相关提及）都 <= 截止轮；每个事实在截止轮前至少有一条证据
  V3 用历史文件里的时间重算等待天数，与桶一致（容差 ±1 天）
  V4 date_math 用 cal.py 重算：事件日、星期都要一致
  V5 题面不含 rubric 里 required / forbidden 的原句（去标点后 >= 8 字的片段）
  V6 同一事件族不跨 dev / test（备用组算封存一侧）；splits 与 exam-inputs 一致，备用组不在 exam-inputs
  V7 sources 引文逐字出现在对应轮次的历史文本里；证据轮 <= 总轮数
  V8 rubric 自洽：required 非空、forbidden 非空，且 required 与 forbidden 没有相同条目
  V9 报告（不判失败）：各桶题数、L1–L4 占比、dev/test 占比、每考点 × 桶的最小事实组数
"""
import argparse, collections, datetime as dt, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = {"id", "persona", "history_file", "history_sha256", "now", "cutoff_turn", "question"}
BUCKET_SHIFT_OK = {"M01-G093/d015"}   # now moved to the previous Sunday morning (see review-only/rewrite-table.jsonl)
HKEYS = {"轮次", "逻辑时间", "用户消息", "助手回复", "日"}
ID_MAIN = re.compile(r"^M\d{2}-G\d{3}/(d\d{3}|x[a-z]\d+[a-z]?)$")
ID_CTL = re.compile(r"^M\d{2}-K\d{2}$")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def jl(p):
    out = []
    with open(p, encoding="utf-8") as f:
        for n, l in enumerate(f, 1):
            if l.strip():
                out.append(json.loads(l))
    return out


def norm(s):
    return re.sub(r"[\s，。！？、；：,.!?;:“”\"'‘’（）()…—\-]", "", str(s))


class Report:
    def __init__(self):
        self.rows = []

    def add(self, code, ok, msg, detail=None):
        self.rows.append({"check": code, "ok": bool(ok), "msg": msg, "detail": (detail or [])[:8]})

    @property
    def ok(self):
        return all(r["ok"] for r in self.rows)


def load_exam(root=HERE):
    return jl(os.path.join(root, "exam-inputs.jsonl"))


def load_histories(root, manifest):
    hist = {}
    for p, info in manifest["personas"].items():
        hist[p] = jl(os.path.join(root, info["history_file"]))
    return hist


def basic(root, R):
    mp = os.path.join(root, "manifest.json")
    manifest = json.load(open(mp, encoding="utf-8"))
    exam = load_exam(root)
    bad = [i for i, r in enumerate(exam) if set(r) != KEYS]
    R.add("B1", not bad, f"exam-inputs {len(exam)} 行，键集合严格等于白名单", [f"行{i + 1}: {sorted(set(exam[i]) ^ KEYS)}" for i in bad])
    ids = [r.get("id") for r in exam]
    dup = [k for k, v in collections.Counter(ids).items() if v > 1]
    badid = [i for i in ids if not (isinstance(i, str) and (ID_MAIN.match(i) or ID_CTL.match(i)))]
    R.add("B2", not dup and not badid, "id 唯一且格式合法", dup + badid)
    pers = manifest["personas"]
    errs = []
    for p, info in pers.items():
        fp = os.path.join(root, info["history_file"])
        if not os.path.exists(fp):
            errs.append(f"{p}: 缺历史文件")
        elif sha256(fp) != info["sha256"]:
            errs.append(f"{p}: 历史文件 SHA 与 manifest 不一致")
    for r in exam:
        p = r.get("persona")
        if p not in pers:
            errs.append(f'{r.get("id")}: persona {p} 不在白名单')
        elif r.get("history_file") != pers[p]["history_file"] or r.get("history_sha256") != pers[p]["sha256"]:
            errs.append(f'{r.get("id")}: history_file/history_sha256 与 manifest 不一致')
    R.add("B3", not errs, "persona 白名单；history_file 存在；SHA 三方一致", errs)
    hist = load_histories(root, manifest)
    herr = []
    times = {}
    for p, rows in hist.items():
        tl = []
        for i, r in enumerate(rows, 1):
            ks = set(r)
            if not (HKEYS <= ks <= HKEYS | {"会话"}):
                herr.append(f"{p} 第{i}行键不合法: {sorted(ks)}")
                break
            if r["轮次"] != i:
                herr.append(f"{p} 轮次不连续于第{i}行")
                break
            tl.append(dt.datetime.fromisoformat(r["逻辑时间"]))
            if len(tl) > 1 and tl[-1] < tl[-2]:
                herr.append(f"{p} 时间倒退于第{i}轮")
                break
        times[p] = tl
        if len(tl) != manifest["personas"][p]["turns"]:
            herr.append(f"{p} 轮数 {len(tl)} 与 manifest {manifest['personas'][p]['turns']} 不一致")
    R.add("B4", not herr, "历史文件键、轮次连续、时间单调", herr)
    perr = []
    for r in exam:
        try:
            now = dt.datetime.fromisoformat(r["now"])
            if now.tzinfo is None:
                perr.append(f'{r["id"]}: now 缺时区')
                continue
            tl = times[r["persona"]]
            last = max([i + 1 for i, t in enumerate(tl) if t <= now], default=0)
            if r["cutoff_turn"] != last:
                perr.append(f'{r["id"]}: cutoff_turn {r["cutoff_turn"]} != 不晚于 now 的最后一轮 {last}')
        except Exception as e:
            perr.append(f'{r.get("id")}: {e}')
    R.add("B5", not perr, "now 合法，cutoff_turn = 不晚于 now 的最后一轮", perr)
    qerr = [r["id"] for r in exam if not (isinstance(r.get("question"), str) and r["question"].strip())]
    R.add("B6", not qerr, "question 非空", qerr)
    merr = []
    for rel, h in manifest["files"].items():
        fp = os.path.join(root, rel)
        if not os.path.exists(fp):
            merr.append(f"缺文件 {rel}")
        elif sha256(fp) != h:
            merr.append(f"SHA 不一致 {rel}")
    R.add("B7", not merr, f"manifest {len(manifest['files'])} 个文件的 SHA256 全部一致", merr)
    return manifest, exam, hist


def verify_all(root, R, manifest, exam, hist):
    ro = os.path.join(root, "review-only")
    sys.path.insert(0, ro)
    import cal  # review-only/cal.py（脚本算日期用）
    cases = {}
    for p in manifest["personas"]:
        for c in jl(os.path.join(ro, f"cases-{p}.jsonl")):
            cases[c["case_id"]] = c
    keys = {k["id"]: k for k in jl(os.path.join(ro, "answer-key.jsonl"))}
    splits = json.load(open(os.path.join(root, "splits.json"), encoding="utf-8"))
    qpath = os.path.join(root, "quarantine", "quarantine.jsonl")
    qids = {q["id"] for q in jl(qpath)} if os.path.exists(qpath) else set()
    gsplit = splits["group_split"]
    exam_ids = {r["id"] for r in exam}
    # V1
    miss = [i for i in exam_ids if i not in keys]
    reserve_ids = {k["id"] for k in keys.values() if k.get("kind") == "main" and gsplit.get(k["case_id"]) == "reserve" and k.get("probe_type") in (None, "legacy")}
    extra = [i for i, k in keys.items() if i not in exam_ids and i not in reserve_ids]
    inq = sorted((exam_ids | set(keys)) & qids)
    R.add("V1", not miss and not extra and not inq, f"exam {len(exam_ids)} 题均有答案；answer-key 除备用组 {len(reserve_ids)} 题外全在 exam；隔离区 {len(qids)} 题不在其中", miss + extra + inq)
    ex = {r["id"]: r for r in exam}
    # V2 / V3 / V4 / V5 / V7 / V8
    e2, e3, e4, e5, e7, e8 = [], [], [], [], [], []
    ndate = 0
    for iid, r in ex.items():
        k = keys.get(iid)
        if not k:
            continue
        p = r["persona"]
        rows = hist[p]
        cut = r["cutoff_turn"]
        if k.get("probe_type") not in (None, "legacy"):
            continue                         # new 2.1 rows are checked by new_checks()
        if k["kind"] == "main":
            c = cases[k["case_id"]]
            ins = next(i for i in c["instances"] if i["id"] == iid)
            anchors = k["anchors"]
            if not anchors:
                e2.append(f"{iid}: 无锚点")
            for a in anchors:
                if a["last_turn"] > cut:
                    e2.append(f'{iid}: 锚点轮 {a["last_turn"]} > 截止轮 {cut}')
            for f in c["facts"]:
                if not f["mention_turns"] and not f["evidence"]:
                    continue  # “没说清/没解释”类事实：历史里本来就没有，不要求证据
                if not any(ev["turn"] <= cut for ev in f["evidence"]) and not any(t <= cut for t in f["mention_turns"]):
                    e2.append(f'{iid}: 事实 {f["fact_id"]} 截止轮前无证据')
            if anchors:
                now = dt.datetime.fromisoformat(r["now"])
                ages = [(now - dt.datetime.fromisoformat(rows[a["last_turn"] - 1]["逻辑时间"])).total_seconds() / 86400 for a in anchors]
                wait = min(ages)
                if abs(wait - k["interval_days"]) > 1.0 and abs(round(wait) - k["interval_days"]) > 1 and iid not in BUCKET_SHIFT_OK:
                    e3.append(f'{iid}: 重算等待 {wait:.2f} 天，桶 {k["interval_days"]}')
            dm = k.get("date_math")
            if dm:
                ndate += 1
                try:
                    wd = cal.weekday_cn(dt.date.fromisoformat(dm["event_date"]))
                    if wd != dm["event_weekday"]:
                        e4.append(f'{iid}: 事件日 {dm["event_date"]} 星期应为 {wd}，记录为 {dm["event_weekday"]}')
                    if dm["rule"] in cal.RULES:
                        got = str(cal.apply_rule(dm["rule"], dt.date.fromisoformat(dm["speaker_date"]), dm.get("arg")))
                        if got != dm["event_date"]:
                            e4.append(f'{iid}: 规则 {dm["rule"]} 重算得 {got}，记录为 {dm["event_date"]}')
                except Exception as e:
                    e4.append(f"{iid}: date_math 无法重算 {e}")
            for s in c["sources"]:
                if s["turn"] > len(rows):
                    e7.append(f'{iid}: 证据轮 {s["turn"]} 超出历史')
                    continue
                row = rows[s["turn"] - 1]
                if norm(s["quote"]) not in norm(row["用户消息"] + row["助手回复"]):
                    e7.append(f'{c["case_id"]}: 引文不在第{s["turn"]}轮: {s["quote"][:20]}')
        rub = k["rubric"]
        qn = norm(r["question"])
        for field in ("required", "forbidden"):
            for item in rub.get(field, []):
                ni = norm(item)
                if len(ni) >= 8 and ni in qn:
                    e5.append(f"{iid}: 题面含 rubric.{field} 原句「{item[:24]}」")
        if not rub.get("required") or not rub.get("forbidden"):
            e8.append(f"{iid}: required/forbidden 为空")
        both = {norm(x) for x in rub.get("required", [])} & {norm(x) for x in rub.get("forbidden", [])}
        if both:
            e8.append(f"{iid}: required 与 forbidden 有相同条目")
    R.add("V2", not e2, "锚点轮 <= 截止轮；每个事实截止轮前有证据", e2)
    R.add("V3", not e3, "重算等待天数与桶一致（±1 天）", e3)
    R.add("V4", not e4, f"date_math 重算一致（{ndate} 道带日期运算的题）", e4)
    R.add("V5", not e5, "题面不含 rubric 原句", e5)
    R.add("V7", not e7, "sources 引文逐字在历史里", e7)
    R.add("V8", not e8, "rubric 自洽", e8)
    # V6
    fam = collections.defaultdict(set)
    for cid, c in cases.items():
        side = "dev" if gsplit.get(cid) == "dev" else "test"
        fam[c["family"] or cid].add(side)
    e6 = [f"{f}: 同时在 dev 和 test" for f, s in fam.items() if len(s) > 1]
    e6 += [f"{r['id']}: 备用组题目出现在 exam-inputs" for r in exam if r["id"] in reserve_ids]
    for u, members in splits.get("units", {}).items():
        if len({gsplit[m] if gsplit[m] == "dev" else "test" for m in members}) > 1:
            e6.append(f"族 {u} 跨 dev/test")
    R.add("V6", not e6, "同一事件族不跨 dev/test；备用组不在 exam-inputs", e6)
    # V9 report
    main = [k for k in keys.values() if k["kind"] == "main" and k["id"] in exam_ids and k.get("probe_type") in (None, "legacy")]
    bucket = collections.Counter(k["interval_days"] for k in main)
    level = collections.Counter(k["difficulty"]["level"] for k in main)
    tot = sum(level.values()) or 1
    sp = collections.Counter(k["split"] for k in keys.values() if k["id"] in exam_ids)
    cell = collections.defaultdict(set)
    for k in keys.values():
        if k["kind"] == "main" and k["id"] in exam_ids and k.get("probe_type") in (None, "legacy"):
            for t in k["content_tags"]:
                cell[(t, k["interval_days"])].add(k["case_id"])
    mn = min((len(v) for v in cell.values()), default=0)
    R.add("V9", True, "报告：桶 %s；L1–L4 占比 %s；split %s；考点×桶最小事实组数 %d" % (dict(sorted(bucket.items())), {l: round(level[l] / tot, 3) for l in sorted(level)}, dict(sp), mn))


def new_checks(root, R, manifest, exam, hist):
    ro = os.path.join(root, "review-only")
    keys = {k["id"]: k for k in jl(os.path.join(ro, "answer-key.jsonl"))}
    ex = {r["id"]: r for r in exam}
    new = {i: k for i, k in keys.items() if i in ex and k.get("probe_type") not in (None, "legacy")}
    n1, n2, n3, n4, n5, n6 = [], [], [], [], [], []
    twins = collections.defaultdict(list)
    for i, k in new.items():
        r = ex[i]
        rows = hist[r["persona"]]
        cut = r["cutoff_turn"]
        for t in k.get("evidence_turns", []):
            if t > cut:
                n1.append(f"{i}: 证据轮 {t} > 截止轮 {cut}")
        rub = k["rubric"]
        if not rub.get("required") or len(rub["required"]) > 4:
            n2.append(f"{i}: required 为空或超过 4 条")
        if not rub.get("forbidden") and not rub.get("unknown"):
            n2.append(f"{i}: forbidden/unknown 同时为空")
        if k.get("twin_id"):
            twins[k["twin_id"]].append(i)
        if k.get("twin_role") == "early":
            toks = k.get("leak_tokens") or []
            if not toks:
                n3.append(f"{i}: 时间孪生早期题没有哨兵词")
            for tok in toks:
                before = any(tok in (x["用户消息"] + x["助手回复"]) for x in rows[:cut])
                after = any(tok in (x["用户消息"] + x["助手回复"]) for x in rows[cut:])
                if before or not after:
                    n3.append(f"{i}: 哨兵词「{tok}」必须只出现在截止轮之后")
        if k["split"] not in ("dev", "test"):
            n6.append(f"{i}: split 非法")
    for tid, members in twins.items():
        ks = [keys[m] for m in members]
        if len(members) < 2:
            n4.append(f"{tid}: 孪生组只有 {len(members)} 题")
        if len({k["split"] for k in ks}) > 1:
            n5.append(f"{tid}: 孪生成员跨 dev/test")
        if ks[0]["probe_type"] in ("time_twin", "premise_twin") and False:
            pass
        if all(k["probe_type"] == "time_twin" for k in ks):
            qs = {ex[m]["question"] for m in members}
            nows = {ex[m]["now"] for m in members}
            if len(qs) != 1 or len(nows) < 2:
                n4.append(f"{tid}: 时间孪生应同一句话、不同 now")
        if all(k["probe_type"] == "premise_twin" for k in ks):
            if len({ex[m]["now"] for m in members}) != 1 or len({ex[m]["question"] for m in members}) != 2:
                n4.append(f"{tid}: 真假前提孪生应同一 now、两句不同的话")
    R.add("N1", not n1, f"新题 {len(new)} 道：证据轮 <= 截止轮", n1)
    R.add("N2", not n2, "新题 rubric 完整，required <= 4", n2)
    R.add("N3", not n3, "时间孪生早期题的哨兵词只出现在截止轮之后", n3)
    R.add("N4", not n4, "孪生组结构正确", n4)
    R.add("N5", not n5, "孪生成员同在 dev 或同在 test", n5)
    R.add("N6", not n6, "新题 split 合法", n6)
    cnt = collections.Counter((k["probe_type"], k["split"]) for k in new.values())
    R.add("N7", True, "报告：新题类型×split " + json.dumps({f"{a}|{b}": v for (a, b), v in sorted(cnt.items())}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=HERE)
    ap.add_argument("--verify-all", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--load", action="store_true")
    a = ap.parse_args()
    if a.load:
        ex = load_exam(a.root)
        print(len(ex))
        return 0
    R = Report()
    manifest, exam, hist = basic(a.root, R)
    if a.verify_all:
        verify_all(a.root, R, manifest, exam, hist)
        new_checks(a.root, R, manifest, exam, hist)
    if a.json:
        print(json.dumps({"ok": R.ok, "checks": R.rows}, ensure_ascii=False, indent=1))
    else:
        for r in R.rows:
            print(("PASS " if r["ok"] else "FAIL ") + r["check"] + "  " + r["msg"])
            for d in r["detail"]:
                print("      - " + str(d))
        print("ALL PASS" if R.ok else "SOME CHECKS FAILED")
    return 0 if R.ok else 1


if __name__ == "__main__":
    sys.exit(main())
