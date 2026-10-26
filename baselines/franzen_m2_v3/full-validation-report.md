# Stage 3C 完整验证结果

**SUCCESS — Kaggle Version 3 / script version 362506200。** 本次只执行了一次获批的 Save & Run All；没有比赛提交、第二次运行、Stage 1/2 修改、commit 或 push。

| 指标 | 结果 |
|---|---:|
| Notebook 总耗时 | 30,053.5 秒（8 小时 20 分 53.5 秒） |
| 9 小时限制余量 | 2,346.5 秒（39 分 6.5 秒） |
| Benchmark 起止（悉尼 AEDT，10 月 27 日） | 00:34:39–08:45:35 |
| Benchmark 耗时 | 8 小时 10 分 56 秒 |
| 公开游戏与回合数 | 25 个游戏 × 4 次，共 100 回合 |
| 通关 | 33/100 回合，覆盖 12/25 个不同游戏 |
| 累计完成关卡 | 417（含四次重复游戏） |
| 平均公开游戏分数 | 47.93969028（日志显示 47.94） |
| 中位分数 | 46.05 |
| 环境动作 | 21,078 |
| Harness 报告的生成 token | 17,506,945 |
| 观测到的峰值 GPU 显存 / 主机内存 | 94.1/95.6 GiB；122.0/176.9 GiB |
| 剩余 GPU 配额 | 约 21 小时 09 分钟 |

配额来自页面 `Quota: 08:51 / 30 hrs`，按已用 8 小时 51 分钟折算，精确到分钟。47.94 是普通离线公开游戏评测分数；没有官方 Kaggle 排行榜分数。67 个 `gave_up` 回合是预算内未解出的结果，不是 notebook 运行失败。

**已验证与归档**

运行前下载的 Version 2 候选与获批文件 SHA-256 完全一致（`f8e3bf0065a198e6508f738546941d67454eeac74236f244a4de9ee9dc51f4fc`），23 个 cell 源码全部匹配 Franzen 发布 Version 3。输入版本沿用已验证清单；完成后页面再次显示相同五项输入和两个模型 V1。Stage 1/2 的 agent、评测、trace 和原 notebook builder 四个关键文件哈希未变。

完整执行日志、实际 `benchmark.json`、`serve.log`、`diagnostics.html`、`submission.parquet`、100 回合/25 游戏结构化结果、配额/成功截图、811 个远程输出路径及本地文件哈希已保存至 `generated/full_run_362506200/`。远程总输出为 7.03 GB；本地只归档关键结果，未镜像全部请求、视频和轨迹。

100 个 benchmark 结果与完整日志中的 100 条 finished 结果逐项一致；21,078 条 history 与动作总数一致。独立 Parquet 读取通过：2,648 字节，一行，列为 `row_id, game_id, end_of_game, score`，类型为字符串、字符串、bool、int64。实际内容是 `1_0, 1, True, 1`，属于原版普通运行的占位文件。正式评测由 competition gateway 重新执行并生成真实提交产物；本次没有触发它。

**复现与基础设施限制**

- 服务随机 seed 为 `549482420`。发布版未固定 seed，因此不能承诺逐步轨迹/得分完全重复。
- Chrome 对已执行 notebook 的导出页明确返回 `ERR_BLOCKED_BY_CLIENT`；运行视图编辑器也曾停在 Loading。未绕过保护。执行后的 `.ipynb` 尚未本地归档，也未完成执行后 cell/输入 ID 的二次导出哈希检查；运行前精确校验及实际日志已保留。
- 有效容器 digest 为 `57e612b484cf3df5026ee4dcc3cb176974b22b2bc0937fb1e16132a8be4cb13c`，日志标为 Latest Container Image，但编辑器保留 original environment 2026-05-27。实际 SGLang/Torch/CUDA 与发布配置一致；容器标签与 pin 的映射仍不确定。
- `benchmark.json` 的 `final_generated_tokens` 全为零；token 总数使用 execution.log 的 finished 记录求和并与最终汇总核对。日志的 total wallclock 是各回合累计时间，不能作为 notebook 实际运行时间。
- 没有 CUDA OOM 或推理服务 traceback。模型 Python 工具产生过 SyntaxWarning，未造成 notebook 失败。
- 9 小时通过仅验证本次 25 个公开游戏的普通运行；隐藏 competition gateway 的时间、得分及产物仍未验证。

**逐游戏结果（四次游戏的平均分与平均关卡）**

| 游戏 | 通关回合/4 | 平均分 | 平均关卡/总关卡 | 总动作 |
|---|---:|---:|---:|---:|
| ar25 | 4/4 | 100.00 | 8.00/8 | 1275 |
| bp35 | 0/4 | 3.02 | 1.25/9 | 248 |
| cd82 | 3/4 | 57.46 | 4.50/6 | 652 |
| cn04 | 1/4 | 66.67 | 4.75/6 | 954 |
| dc22 | 0/4 | 36.94 | 3.50/6 | 1316 |
| ft09 | 3/4 | 86.90 | 5.50/6 | 376 |
| g50t | 0/4 | 2.48 | 0.50/7 | 514 |
| ka59 | 0/4 | 19.17 | 2.50/7 | 943 |
| lf52 | 0/4 | 1.82 | 1.00/10 | 372 |
| lp85 | 4/4 | 100.00 | 8.00/8 | 634 |
| ls20 | 0/4 | 19.90 | 3.00/7 | 1446 |
| m0r0 | 1/4 | 59.65 | 4.00/6 | 1109 |
| r11l | 4/4 | 100.00 | 6.00/6 | 469 |
| re86 | 0/4 | 50.00 | 5.50/8 | 1783 |
| s5i5 | 0/4 | 37.53 | 4.25/8 | 978 |
| sb26 | 4/4 | 89.28 | 8.00/8 | 727 |
| sc25 | 1/4 | 55.94 | 4.50/6 | 1295 |
| sk48 | 0/4 | 4.86 | 1.00/8 | 401 |
| sp80 | 0/4 | 39.35 | 3.75/6 | 613 |
| su15 | 0/4 | 10.56 | 2.50/9 | 574 |
| tn36 | 0/4 | 10.24 | 1.50/7 | 619 |
| tr87 | 3/4 | 76.19 | 4.75/6 | 935 |
| tu93 | 3/4 | 92.73 | 8.75/9 | 1050 |
| vc33 | 2/4 | 73.34 | 5.75/7 | 876 |
| wa30 | 0/4 | 4.45 | 1.50/9 | 919 |

完整精确结果见 `generated/full_run_362506200/per-game-results.json`；Parquet 独立验证见 `parquet-validation.json`；其他断言与哈希见 `full-validation.json`、`full-validation-run.json`。只读查看本次运行：

https://www.kaggle.com/code/panxiyuan/franzen-m2-v3-baseline?scriptVersionId=362506200

重新检查本地核心结果（不使用 GPU、不启动 Kaggle）：

```bash
cd /Users/xiyuanpan/ARC-AGI-3
python3.12 - <<'PY'
import json
from pathlib import Path
p = Path('baselines/franzen_m2_v3/generated/full_run_362506200')
v = json.loads((p / 'full-validation.json').read_text())
assert v['duration_within_32400'] and v['all_100_benchmark_results_match_finished_log_rows']
assert v['parquet_validation']['valid_parquet']
print(v)
PY
```

完成监控已删除。官方提交与第二次完整运行均需另行明确批准。
