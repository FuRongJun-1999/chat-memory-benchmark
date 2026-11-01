# 大肥鱼 · 记忆系统评测

各种记忆框架，到底能记住什么，又会忘掉什么？这个项目把长时间聊天中的事实、改口、约定和边界整理成可检查的题目，用同一套规则比较不同系统。

目前关注**每天约两轮、跨度最长半年**的超轻度聊天场景。一轮指一条用户消息和一条助手回复。它不代表高频聊天、多人群聊或真实用户的全部使用情况。

**首版公开测试方法、接入协议、可运行的读题工具、独立虚构示例及本轮汇总成绩。正式六人物考卷暂未公开；这里的示例不能复现视频中的分数。**

## 已经测过哪些

共 **7 个社区项目／方案，加 1 个 Qwen RAG 对照**。下面是项目目录，不是混合排名：完整卷、共同已答题和旧卷试跑的范围不同，比较请看各行链接里的同卷成绩。

| 项目／上游 | 作者 | 测试状态与成绩（通过 / 已答） |
| --- | --- | --- |
| [冷热记忆方案（ARCHEON）](https://github.com/ARCHEON999/Companion-AI-Memory-Context-Token-Optimization) | 原无奇变 / ARCHEON999 | 按公开方案复现；完整卷 [356 / 714](results/2026-11-01-first-four.md) |
| [SeekMemory](https://github.com/NeverENG/SeekMemory) | BangBang在coding / NeverENG | 原版插件，开启 Dream；完整卷 [230 / 714](results/2026-11-01-first-four.md) |
| [digital-life-core](https://github.com/mashangshui/digital-life-core) | 温水 / mashangshui | 原生核心与迁移入口；完整卷 [233 / 714](results/2026-11-01-first-four.md) |
| [dsh-world](https://github.com/chenkezhen480/dsh-world) | CyreneAKen | **旧卷部分试跑，按预算停测**；未参加新卷完整比较，见[运行说明](docs/tested-configurations.md#dsh-world) |
| [dsh-soul](https://github.com/icyaaaww/dsh-soul) | 糖霜Official | 完整卷 418 / 714；合辑共同题 [402 / 687](results/2026-11-01.md) |
| [SurfCore](https://github.com/Mieksido/surfcore) | 玛露Marrow | 完整卷 123 / 714；合辑共同题 [122 / 687](results/2026-11-01.md) |
| [dsh-rofm](https://github.com/wall1234567/dsh-rofm) | 鄙人乃路人甲 | 降低测试归档阈值后中断；已答 [242 / 687](results/2026-11-01.md)，另有 27 题未答 |
| Qwen RAG（本评测搭建的检索对照） | Qwen 模型团队；检索流程由本评测搭建 | 完整卷 [596 / 714](results/2026-11-01-first-four.md)；合辑共同题 [574 / 687](results/2026-11-01.md) |

各项目的固定版本、实际接入方式、维护开关和局限统一放在[测试配置与局限](docs/tested-configurations.md)。作者署名沿用评测登记信息。

## 从哪里开始

| 你想做什么 | 看这里 |
| --- | --- |
| 看考什么、怎么判 | [测试方法](docs/methodology.md) |
| 直接看示例题、答案和证据 | 下载仓库后打开 [示例题.html](demo/示例题.html)，或在线读 [示例题.md](demo/示例题.md) |
| 把示例接到自己的系统 | [接入说明](docs/integration.md)、[读题工具](demo/read_exam.py) |
| 核对所有已测系统版本和配置 | [测试配置与局限](docs/tested-configurations.md) |
| 看之前四期的完整成绩 | [冷热方案、SeekMemory、digital-life-core、Qwen：714 题](results/2026-11-01-first-four.md) |
| 看新增三项目合辑的成绩 | [Soul、SurfCore、ROFM、Qwen：共同 687 题](results/2026-11-01.md) |
| 了解哪些公开、哪些保留 | [发布范围](docs/publication.md) |

## 五分钟运行公开示例

只需 Python 3.10 或更新版本，无第三方依赖、无 API key，也不会产生模型费用。

```sh
git clone https://github.com/Ornn8/memory-system-benchmark.git
cd memory-system-benchmark
python demo/read_exam.py --verify-all
python demo/read_exam.py --id PUB01-C001/d45 --output question.json
python -m unittest discover -s tests -v
```

`question.json` 包含题目、考试时间和该时刻允许读取的历史，没有参考答案。**历史是给记忆系统逐轮处理的，不能把整个 JSON 直接塞进作答模型冒充记忆测试。** 具体做法见接入说明。

示例规模：一个虚构人物、182 天、360 轮对话、27 个独立事实组；每组在当天、3 天、15 天、45 天提问，共 108 个实例。重复问同一事实不算新增独立事实。每个考点和时间档仅有一道示例，供理解和接入，不据此排名。

## 我们怎么理解“记住了”

先把已有的用户消息和助手回复按时间交给系统自己的记忆流程，再从独立会话提问。更早的内容需要由系统的记忆或检索机制提供，不能偷偷附上完整聊天。

成绩写“通过几题 / 实际考几题”。只判事实、主体、时间和边界，不判说话风格。忘了、记错了、没有证据却编了，以及该保密时泄露了，分别记录。跨时间召回穿插在各考点里，不另造一个与内容脱节的总分。

## 公开内容的边界

- 本示例的人物、事件、问题和答案全部为独立虚构内容，不含真实用户聊天或正式考卷内容。
- 示例附标准答案，适合讲解、调试和研究，不能再当作未曝光的考试。
- 汇总成绩来自另一份冻结私有考卷，完整原始答卷未在本仓库发布，因此当前不提供正式分数的端到端公开复现。
- 当前提供读题与输入边界校验代码、系统接入协议和实际配置说明；**未打包私有评测环境的完整调度器、模型网关或可一键启动全部项目的适配器**。
- 项目链接和作者署名用于溯源，不代表第三方作者认可本次测试结论。

## 许可与反馈

本仓库自行编写的代码、文档和虚构示例使用 [MIT 许可](LICENSE)。第三方项目使用各自许可；仓库不捆绑其源码。

欢迎通过 Issue 指出题意歧义、错误证据或接入差异，请附公开示例题号、版本和复现步骤。不要提交密钥、私人对话或真实用户身份资料。订正会保留变更记录，不以某个系统得分高低为理由改题。
