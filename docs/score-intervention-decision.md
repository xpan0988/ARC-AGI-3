# Franzen M2 V3：得分干预决策

2026-10-28（AEDT）｜完整归档审计与独立候选 CPU 验证｜提交版 baseline 未修改

**实施状态更新：独立候选已实现、默认关闭，15 项 CPU 回归通过；提交版 V3 未改。仅 GO 小规模 GPU A/B，尚未启动，等待 review。** 本文第 1–5 节记录原归档审计与预设门槛；第 6 节记录本轮实现和验证。

## 结论

**GO：只建议验证“Python 硬超时后保留上次成功导出的 helper 快照”这一项最小修复。不是直接采用，也不在本轮启动 GPU。** 不建议改模型、调度器，或新增世界模型、critic、强制验证架构。

对核心问题的回答：**证据更接近“已有能力发挥不稳定”，而不是“模型根本不具备解题能力”；但不能因此把主要失分都归咎于 harness。** 四组成功对照证明相同模型和 harness 能完成这些公开游戏。失败记录中的直接卡点，多为错误目标、错误动力学模型、错误搜索约束及其反复修补；同时，harness 确实存在一种跨游戏重复发生、会破坏已有程序性知识的清空行为。它是当前最有把握定位和单独测试的可修复损失，不是已证实的最大得分瓶颈。

47.94 是 25 个公开游戏、四次尝试的验证均分；24.47 是用户确认的正式 public leaderboard 分数。**本包属于前者，不能用其中五个失败解释两分数之间的差额，也没有隐藏游戏上的因果证据。**

## 1. 数据完整性与审计范围

`~/Downloads` 顶层未找到 ZIP；本轮实际找到并使用的是用户已放入项目的 [downloads/results.zip](/Users/xiyuanpan/ARC-AGI-3/downloads/results.zip)，修改时间为 10 月 27 日 23:38 AEDT。

| 核验项 | 结果 |
| --- | --- |
| 压缩包 | 2,238,365,092 bytes；811 个成员；解压总大小 7,033,630,219 bytes |
| SHA-256 | `adcc26f3118ba5d0c385cd52f1b739c728ab646647dfeeec3b3f11b316d8b327` |
| 内容 | 100 份 transcript、100 份事件 JSONL、100 份 viewer JSON，以及请求日志、诊断等 |
| 完整性 / 解压安全 | 全部 811 个成员 CRC 通过；无重复成员、绝对路径、`..` 跳转、符号链接或加密项；未执行包内代码或 pickle |
| 运行身份 | 包内 benchmark、diagnostics、serve.log、Parquet 的 SHA-256 均与 `full_run_362506200/` 现有文件完全一致 |
| 九份目标 transcript | 合计 29,547,709 bytes；单份约 2.37–4.62 MB；包含末关 L6/L9/L8，直至 WIN 或截止停止，超出旧的 102,400 字符预览范围 |
| 动作对齐 | 九回合共 2,826 个事件动作；数量、顺序、动作 ID 和鼠标坐标逐项匹配 benchmark |

只按白名单解压目标回合及核验文件，目录为 [arc-score-evidence-7s_zvwuw](/private/tmp/arc-score-evidence-7s_zvwuw)。[完整性清单](/private/tmp/arc-score-evidence-7s_zvwuw/integrity.json) 保留成员大小、CRC 和哈希。下文引用原始文件的行号；若临时目录被系统清理，可从 ZIP 内同名成员复核。未覆盖旧资料。

方法：九回合按关卡建立顺序索引，核读起始目标判断、跨关知识、末关假设—代码—结果及关键修正；重复系统提示和原始工具参数的重复转录不当作新推理。另对全部 100 份 transcript 做有界的精确超时扫描，再仅检查命中的 36 份请求日志，按 `tool_call_id` 去重。**没有把全文扫描当作人工逐句因果标注，也没有读取游戏实现寻找答案。**

## 2. 成功与失败的关键差异

这些回合不是配对实验。以下“分歧”是观察到的行为差异，不是单因素因果效应。

| 游戏 | 失败回合：完成关数 / 实际分数 | 成功对照：完成关数 / 实际分数 |
| --- | --- | --- |
| M0R0 | p0：5/6；71.43 | p1：6/6；100 |
| CN04 | p0：5/6；71.43 | p3：6/6；100 |
| TU93 | p1：8/9；80 | p2：9/9；100 |
| SC25 | p3：5/6；71.43 | p2：6/6；87.63 |
| S5I5 | p2：7/8；77.78 | 四次均未完成全游戏 |

分数来自归档 [benchmark.json](/private/tmp/arc-score-evidence-7s_zvwuw/benchmark.json)，保留部分进展与动作效率计分；完成游戏不必然得到 100 分。

### M0R0：相邻不等于已达到目标

**目标与学习。** 两边物体受镜像控制；模型逐步学会门、压板、可选中移动的小块，以及用小块阻挡一侧来打破同步运动。p0 早期把过关解释为“相交/交换”，p1 用两个受控物体到达同一位置作为搜索目标。

**关键分歧。** p0 末关的自写搜索找不到 swap 后，将目标改成“相邻”，又在相邻未过关后追加“必须在门口相邻”。它确实会修正被反驳的假设，但修正反复引入未经证实的新目标；不是始终无视反馈。[p0 L28737](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/m0r0-492f87ba_p0.txt:28737)、[L31072](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/m0r0-492f87ba_p0.txt:31072)、[L33075](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/m0r0-492f87ba_p0.txt:33075)。

p1 先用探针修正门和墙的模型，再从**当前实际状态**重搜、逐步比较预测与观察。最后一条 RIGHT 的日志预测双方同时到 `(34,18)`，真实返回 `RUN COMPLETE`。它也遇到状态读取器把同侧物体识别成 `None` 的错误，但通过集合比较修正后继续执行。[p1 L24837](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/m0r0-492f87ba_p1.txt:24837)、[L25168–25253](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/m0r0-492f87ba_p1.txt:25168)。

**最后卡点：** p0 已能控制机关，却仍在猜胜利条件；不是已有完整正确解法仅被工具类型错误阻断。分类：目标建模、状态读取和规划；另有超时丢 helper 的放大因素。p0 在关 5→6 的超时后丢掉 73 个已保留函数，随后明确说需要从头重建；不能据此断言它导致了错误目标。[p0 L22045–22230](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/m0r0-492f87ba_p0.txt:22045)。

### CN04：搜索失败混合了形状、增长机制与程序约束错误

**目标与学习。** 两回合都从插接形状出发，通过移动、旋转、选中不同物体发现红色端点和白色生长点，前几关已验证配对端点可过关。

**关键分歧。** p0 在末关先拿初始形状搜索，反复怀疑“全部连接”“全部配对”“允许实体重叠”等目标/约束，甚至回查早期关卡重新推导。连接起来未过关，是有效反证；但有上限的搜索无解，不足以反驳目标。它直到后段才系统重建生长状态；最终找到 72 个候选布局，尚未完成物理验证和执行就结束。[p0 L35553](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/cn04-2fe56bfb_p0.txt:35553)、[L41615](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/cn04-2fe56bfb_p0.txt:41615)、[L43162](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/cn04-2fe56bfb_p0.txt:43162)。

p3 也曾得到零解，也写错过剪枝。区别在于它检查一个本应合法的具体放置，发现 `len(free)%2` 的剪枝忽略了未放物体的端点数，修正后找到布局；另写 verifier 检查端点配对与重叠，然后 30 动作批次真实返回 WIN。[p3 L21385–21404](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/cn04-2fe56bfb_p3.txt:21385)、[L21669–21794](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/cn04-2fe56bfb_p3.txt:21669)。

**最后卡点：** p0 的可执行状态模型/搜索还未验证完，而非“模型已输出已证实正确的最终动作”。分类：视觉到几何的编码、机制学习、搜索程序正确性与跨关知识使用。p0 四次超时清空 helper；p3 也发生一次、丢 61 个函数并恢复成功，因此清空不是失败的充分条件。[p3 L20472–20755](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/cn04-2fe56bfb_p3.txt:20472)。

### TU93：错误追踪者模型驱动重复规划和死亡

**目标与学习。** 两回合都很早识别“穿越迷宫到绿色目标”，逐关学习敌人朝向、巡逻与遮挡；这里没有直接证据表明主要目标错误。

**关键分歧。** p1 在第 8 关就以“某规则下搜索可解”支持击杀/追踪假设，随后第 9 关围绕贪心追逐、lag、tie-break、是否被巡逻者阻挡不断切换规则。它会查历史和修正规则，但“能搜出解”多次先于经验验证；遮挡时的敌人位置也被猜错。末段出现第 5 次死亡，仍在调整规则。[p1 L18940](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/tu93-0768757b_p1.txt:18940)、[L21845](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/tu93-0768757b_p1.txt:21845)、[L26347](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/tu93-0768757b_p1.txt:26347)、[L29747](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/tu93-0768757b_p1.txt:29747)。

p2 在第 8 关把实际玩家/追踪者序列逐步对齐，识别“沿玩家路径落后两步”；第 9 关带入该模型，结合巡逻相位搜索并校验。它同样有超时、坐标步长、路径回溯 KeyError，但分别修正后完成。[p2 L16892](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/tu93-0768757b_p2.txt:16892)、[L21089](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/tu93-0768757b_p2.txt:21089)、[L21945](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/tu93-0768757b_p2.txt:21945)。

**最后卡点：** 动力学与隐藏/遮挡状态估计不可靠，错误模型下规划再多也不能稳定过关。p1 没有 Python 硬超时，故拟议 helper 修复**不能直接解决此例**。不据此声称真正的游戏实现就是某个模型假设。

### SC25：先过度泛化机制，最终已有收尾计划被停止

**目标与学习。** 两回合都已学会把受控块送入目标，利用图案改变大小、传送和清除障碍。p3 把 2×2 状态下反复回到同一处的观察，推广为中间入口不能通过传送到达，反复测试并耗尽一次关内预算。p2 对不同尺寸和位置分别测连通性、传送目标，较早进入正确区域。[p3 L22580–23092](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/sc25-635fd71a_p3.txt:22580)、[p2 L25997–26367](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/sc25-635fd71a_p2.txt:25997)。

**关键执行证据。** p3 最后生成七动作收尾批次，实际只执行六个，返回 `stop_reason: stopped`，剩一条 UP；不是模型忘记发出计划，也不是 no-op guard。[p3 L26662–26687](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/sc25-635fd71a_p3.txt:26662)。失败最后动作事件与 p2 过关前一动作事件的 **64×64 棋盘全部 4096 像素完全相同**；p2 随后 UP 得到 WIN：[失败事件第534行](/private/tmp/arc-score-evidence-7s_zvwuw/artifacts/sc25-635fd71a_p3_events.jsonl:534)、[成功事件第471–472行](/private/tmp/arc-score-evidence-7s_zvwuw/artifacts/sc25-635fd71a_p2_events.jsonl:471)。

这是“已有有效收尾能力没有兑现”的最强样本。**像素一致不保证隐藏状态一致，仍不是严格反事实证明。** 源码在批次每一步前检查 `should_stop()`，可返回 `stopped`；结合结束时间，与资源截止一致。[执行路径](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/notebook-v3.py:8532)。不据这一例建议放宽截止：公开运行余量不等于隐藏评测余量，也不能拿增加动作/GPU预算冒充相同预算的改进。

### S5I5：最后仍有未解决的机制假设

**目标与学习。** 前七关通过探针和代码逐步学会杆件控制、父子位移、旋转、碰撞及点与目标的关系。第 8 关新增联动和包围结构；模型确认一些点击同时改变外部杆和内部臂，并修正过按钮坐标和局部裁剪错误。

**卡点。** 模型从一个臂的最大伸长，推断带点杆也到不了目标，转而测试“任意杆覆盖目标”；覆盖后未过关，便正确否定此猜测。随后又准备测试“内部臂到极限时，外部杆能否继续部分增长”。这个关键规则尚未得到观察验证，不能说最终十二次点击必能过关。[L32975](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/s5i5-18d95033_p2.txt:32975)、[L34154–34277](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/s5i5-18d95033_p2.txt:34154)。

最后 Python 输出 `rot x2 done`，但没有新增动作事件，臂的方向也未变，状态为 `stop_requested`：程序把未执行的 action 返回当作正常结束来打印；不能据该文字认定旋转成功。[L34725–34769](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/s5i5-18d95033_p2.txt:34725)。分类：机制约束泛化、状态/执行结果解释与截止中断；无成功对照，不判定最终计划正确。

## 3. 跨游戏共性：已观察与尚未证明的区别

| 共性 | 支持程度 / 解释边界 |
| --- | --- |
| 用错误或未校验的内部模型解释“搜索无解”，再改目标/规则 | M0R0、CN04、TU93、S5I5 均有实例；不是都拒绝修正，也不是缺少探索工具。成功对照会检查局部预测、程序约束并修复。尚无证据说明再加一段泛化提示就能稳定改善。 |
| 同色物体合并、遮挡、坐标尺度或状态模式导致读取器错误 | 两臂都出现；成功回合也需修复。现有 segmentation、history、动画足以支持多次成功修正，不能把它概括成“没有视觉/记忆能力”。 |
| 函数外变量消失 / 普通 Python 编程错误 | `ROTS6`、`P6`、`ADJ9b` 等 NameError，与已明确告知的“变量不跨调用保存”有关。不是下述 helper 库清空缺陷；不建议把所有变量永久保留。 |
| **硬超时导致已成功保留的 helper 全部丢失** | **直接请求证据 + 源码因果链成立**；跨 18 个游戏。它会使已有解析器、模拟器和执行器需要重建，但不能证明所有失分因此发生。 |

全量有界扫描结果：100 回合中 **50 次硬超时**；后续请求里的实际 `function_retention` 记录确认 **49 次清空非空库**，涉及 **36 回合 / 18 游戏**，合计删除 **1,137 个函数快照条目**（含重复清空，非 1,137 项独立知识）。36 回合最终 **16 胜、20 未胜**，不能用它当失败分类器。九个重点回合内有九次清空、289 个条目；既影响失败，也影响成功对照。

49 次清空之后的**首条**模型回复合计 86,659 completion tokens。该值含必要的新思考，且漏掉后续重建，**既不是净浪费量，也不是可节省 token 的上下界**，不据此换算得分收益。具体运行证据例如 CN04 p0 请求第357行中的清空通知和第358行 usage；模型紧接着说明丢失全部 helper 并重写。[请求原件](/private/tmp/arc-score-evidence-7s_zvwuw/cn04-2fe56bfb_p0_requests.jsonl:357)、[推理 L33015](/private/tmp/arc-score-evidence-7s_zvwuw/transcripts/cn04-2fe56bfb_p0.txt:33015)。

## 4. 唯一建议：超时不提交空 helper 库

**可证伪假设：** 在相同模型、动作规则和资源上限下，硬超时且没有新的函数导出时，保留上次已完成的 helper 快照，会减少无意的知识清空与恢复重写，并让更多已有推理在截止前转化为实际的部分/动作效率加权分数。若只减少重写文本却不改善得分，竞争收益假设未获支持。

**当前机制。** sandbox 超时分支杀死子进程，返回 `error/stdout/action_results`，不返回 `keepable_functions`；宿主 `_record_retained_functions` 却用 `get(...) or []` 构造空库，再执行 `self._kept_functions = kept`。真实已执行动作得到保留，已保留函数被全部删除。**缺失导出与明确导出空库被混为一谈。** [超时返回](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/ARC3-Inference/inference/agent/python_tool_sandbox.py:869)、[记录器](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/ARC3-Inference/inference/agent/tool_agent.py:4614)。

这是应用 Franzen 补丁后的缓存源码；发布 notebook 含同一记录器补丁，并明确启用函数保留、scope=`game`。[notebook 补丁](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/notebook-v3.py:5315)、[启用配置](/Users/xiyuanpan/ARC-AGI-3/local_output/research_refs/franzen/notebook-v3.py:10207)。上述清空也由本次真实请求证实，不仅依赖静态源码。

**最小修改边界（归档审计时未实施；当前实现见第 6 节）：** 只对“明确为工具硬超时，且没有 `keepable_functions` 字段”的返回保留旧快照；告知本次未完成的新定义没有提交。正常导出、明确空导出、验证拒绝、游戏重置及现有 scope 规则保持原义。不能恢复被杀进程里的局部变量，不能提升超时中的新函数为可信定义，不能重放已经执行过的动作。不改 30 秒限时、并发、context、scheduler 或解题提示框架。

**为何可能泛化。** 触发条件来自 Python 生命周期，与公开游戏 ID、布局和答案无关；保留的是模型自己此前生成并成功导出的程序。它不教会模型新规则，而是减少当前 harness 对已有工作成果的破坏。发生率证据强；对得分的正向效应仍未验证，也不能解决 TU93 p1 这类没有超时的错误机制学习。

**回归风险。** 旧 helper 可能带有错误模型；超时调用可能已改变棋盘、重定义函数或跨关，旧快照不代表当前状态。保留它可能延长错误模型的使用。须明确标记回滚边界，重读实时状态并允许重定义；不得声称旧代码“已经语义验证”。已有成功游戏同样受影响，必须作为对照，而不是只筛失败轨迹。

## 5. 最便宜的验证与停止条件

**已完成零 GPU 诊断：** 隔离读取原始记录器的 AST，以最小依赖 stub 注入超时返回包，复现旧库被清空；临时加入上述窄 guard 后，八项断言通过，覆盖旧快照保留、已执行动作记录不变、显式空库仍清空、正常更新/错误导出语义、明确拒绝、非超时异常和无效 metadata。它是返回包/记录器检查，**不是完整 sandbox 集成、模型实验或得分验证**；所有实验代码均在临时目录，baseline 未变。

若决定实现，先补完整 sandbox 的 CPU 回归，尤其测试：超时前已经执行动作或跨关；新定义未提交；旧 bank 的内部依赖保持一致；新游戏/显式拒绝仍清空。任何状态或动作重放错误都直接 NO-GO，不消耗 GPU。

之后最小得分筛选应是**一次封顶 3 GPU 小时、含启动的对照试验**，不重跑全基准：预先固定 M0R0、CN04 和已稳定成功的 R11L；每游戏同一明确环境/推理 seed 对比原版与修复版，共六回合、每臂三个。seed 不等于旧 p 编号，动态 batching 也不保证逐 token 重现。两臂相同队列、wall-clock/token ceiling、权重和全部其余配置；跨臂清理会话状态，完整记录自然超时和恢复。

采用条件必须同时满足：原版出现可比较的清空机会、修复版不再无意清空；恢复重建减少；**实际部分/动作效率加权分数提高，且成功对照不退化**；没有硬时间、动作或 token 预算超支。胜局数只是辅助指标。未触发问题、矩阵未完成、只省文本而分数不升、或出现回归，都视为不支持采用；到上限即停，不自动追加运行。这个小试验仍不能证明隐藏游戏收益。

**最终决定：GO 验证这一项窄修复；当前不采用、不启动 GPU。** 对广泛的目标推断、机制记忆或调度改写维持 NO-GO。此次新证据足以提出可分离测试的改动，但不足以声称 harness 是主要失分原因或承诺任何精确分数增益。

归档审计轮只新增本报告，并在独立临时目录解压、核对证据。原 ZIP、已有 Stage 4E 文件及 baseline 保持原样；无 Kaggle 访问、GPU、提交、训练、模型下载、安装、commit 或 push。

## 6. 实施与 CPU 验证（2026-10-28）

**根因重新核实。** 项目真正可再生的来源是 hash 固定的根目录 Franzen notebook：第 2 格写 release patch，第 4 格复制 Kaggle bundle 并 `git apply`；`baselines/franzen_m2_v3/prepare.py` 保留其 23 格源码。缓存中的 Python 文件不是本轮修改目标。两个应用后文件的完整哈希，以及 release patch 中它们的每个 post-image hunk 均核对通过。超时分支确实不导出函数；记录器确实把缺失字段转成空列表并覆盖旧库。

**准确改动范围：**

| 文件 | 用途 |
| --- | --- |
| [patch.py](/Users/xiyuanpan/ARC-AGI-3/interventions/helper_timeout/patch.py) | 唯一运行时干预源；对已应用 release patch 的独立工作副本做两处插入，先验证两文件完整哈希及唯一锚点 |
| [build.py](/Users/xiyuanpan/ARC-AGI-3/interventions/helper_timeout/build.py) | 独立候选构建；23 个原始 cell source 不变，插入一格安装 overlay；拒绝覆盖既有文件或写入 baseline 路径 |
| [test_helper_timeout.py](/Users/xiyuanpan/ARC-AGI-3/tests/test_helper_timeout.py) | 15 项 CPU 回归，含真实子进程硬超时与动作执行后超时 |
| [franzen_timeout_fixture.py](/Users/xiyuanpan/ARC-AGI-3/tests/franzen_timeout_fixture.py) | 从已核验来源装载真实 sandbox、函数收集/恢复、宿主 dispatch 与生命周期方法，提供假环境适配器 |
| [README.md](/Users/xiyuanpan/ARC-AGI-3/interventions/helper_timeout/README.md) | 构建、开关、源码链与验证边界 |
| 本报告 | 同步实施结果和决定 |

另已生成默认关闭的 [candidate.ipynb](/Users/xiyuanpan/ARC-AGI-3/local_output/helper_timeout/candidate.ipynb)，位于 gitignored 目录；没有运行 notebook。提交版、所有既有 baseline 文件、源码缓存、Stage 1/2/3 文件及已有用户文件未改。

**可靠分类与前后行为。** 开关 `ARC3_PRESERVE_HELPERS_ON_HARD_TIMEOUT` 默认未设置/关闭。关闭时真实 timeout 的模型可见返回和旧库清空行为与原版一致。开启后，仅父进程达到硬截止并杀死子进程的分支添加内部 `_hard_timeout=True`；正常子进程回复不能传入此标记。宿主同时检查完整 envelope、准确 error、空 stdout、动作记录类型；字段缺失、额外字段、显式导出或 rejection metadata 均走原逻辑，避免以错误文字猜测超时。

符合条件时只保留当前旧库，没有回滚动作或棋盘；通知模型本次新/改定义未提交，并明确旧 helper 可能错误。正常导出替换、显式空库清空、验证拒绝、普通异常、同游戏 RESET、新 session，以及 `levelup`/`turn`/`game` 生命周期均保留原语义。跨关后 `levelup` 仍清空；`game` 仍保留并提醒核查新关假设；新 turn 清空、yield resume 不清空。没有独立备份可跨边界复活旧库。

**测试命令与结果：**

```text
.venv/bin/python -m unittest discover -s tests -p 'test_helper_timeout.py' -v
  15 passed；最终运行 14.287s
.venv/bin/python -m unittest discover -s tests -p 'test_exploration.py' -v
  9 passed
.venv/bin/python -m unittest discover -s tests -p 'test_observation_trace.py' -v
  9 passed
.venv/bin/python -m unittest discover -s tests -p 'test_local_instrumentation.py' -v
  1 skipped：原有 opt-in cached real-game integration 未启用
.venv/bin/python baselines/franzen_m2_v3/verify.py
  full_source_parity=true；archive_hashes_valid=true
.venv/bin/python -m interventions.helper_timeout.build
  独立默认关闭候选生成成功
```

CPU 回归不仅检查字典：真实子进程重新定义 helper 后被杀，旧版本及其函数依赖可在下一次调用恢复，新定义不存在；超时前 UP/DOWN 恰执行各一次，动作计数、棋盘和 summary 保持实际状态；跨关与终局 latch、RESET 首动作限制均通过。还实际执行了输出 notebook 的 overlay cell，确认打补丁顺序、默认开关、两个目标文件及 23 格原始源码保留；源码漂移时在写入前拒绝。检查最终运行时代码差异仅为 marker 与保留 guard 两处插入。

**验证边界与风险。** 这里运行了真实 supervisor/bootstrap 和 retention 代码，但宿主方法通过 AST 定向装载，环境、文件序列化、动作名称映射和显示用 fixture；segmentation 不参与。这不是完整 Kaggle bundle 导入、网关集成、模型或得分验证。完整挂载 bundle 的未改区域若与本地应用后文件哈希不同，overlay 会直接拒绝，而不是猜测兼容。原版与候选均出现上游已有的 subprocess 管道 `ResourceWarning`；既有测试的 Matplotlib 缓存落到临时目录；均非测试失败，本轮没有顺带修改这些行为。旧 helper 编码错误机制、状态已改变和随机轨迹回归的风险仍在，得分收益未知。

**决定：GO，仅允许下一次经 review 的小规模 GPU A/B；不代表采用或提交。** 本轮 CPU 门槛通过，未触发停止条件。开关保持关闭；没有 Kaggle 访问、GPU、模型运行、安装、提交、commit 或 push。工作停在此处等待 review，不启动实验。
