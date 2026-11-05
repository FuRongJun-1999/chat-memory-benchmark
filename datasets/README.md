# 六人物记忆测试集

这里公开已出成绩的正式测试集：六个人物的合成历史、714 道题、标准答案和证据。

| 文件 | 内容 |
| --- | --- |
| [histories](natural-timegrid-20261101-v2/histories/) | 六个人物的对话历史 |
| [exam-inputs.jsonl](natural-timegrid-20261101-v2/exam-inputs.jsonl) | 714 道题及对应时间和历史截止点 |
| [answer-key.jsonl](natural-timegrid-20261101-v2/review-only/answer-key.jsonl) | 标准答案、评分规则和证据锚点 |
| [manifest.json](natural-timegrid-20261101-v2/manifest.json) | 文件校验值及原始版本标识 |
| [read_exam.py](natural-timegrid-20261101-v2/read_exam.py) | 离线校验与读题 |

在仓库根目录执行：

```sh
python datasets/natural-timegrid-20261101-v2/read_exam.py --verify-all
python datasets/natural-timegrid-20261101-v2/read_exam.py --id P01-CASE-001/d03
```

先把该题截止点前的历史交给记忆系统，再使用题目测试；标准答案用于判分。查看[测试方法](../docs/methodology.md)和[系统成绩](../README.md#已经测过哪些)。
