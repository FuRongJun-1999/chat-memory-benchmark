# 各项目逐题答卷

这里按项目及测试版本保存六人物正式测试集的逐题回答，题号与[正式题库](../../datasets/natural-timegrid-20261101-v2/)对应。每行 JSON 包含 `id`（题号）、`answer`（原始回答）和 `answer_sha256`（回答 UTF-8 内容的 SHA-256）。

所有文件及条数见 [manifest.json](manifest.json)。多数为 714 题；`dsh-rofm-legacy` 为旧版中断时的 687 题，`mnemon-vector-partial` 为保留的 539 份回答。不同版本各自保存，不合并计算。

`dsh-hippocampus`、`dsh-memory-calendar`、`dsh-fish-memory` 和 `dsh-memory-brain` 是近期新完成的六人物答卷；其他文件包括已有成绩的项目、重测和独立运行版本。作者自测的 [neo4j 答卷](../2026-11-05-dsh-neo4j-answers.jsonl)仍保留在原位置。

Hippocampus 和 Calendar 的考试会话调用过记忆写入工具；Calendar 的后续题存在读取前题所写记忆的路径。此处保留原始回答，相关成绩仍需进一步核查。
