# DPO 离线偏好优化

本文档记录从冻结 v5 SFT 挖掘失败样本、构造 chosen/rejected、运行
LLaMA-Factory DPO，到与 SFT 做公平对比的完整过程。所有 Python 命令都直接
使用 `drivevla_sft` 环境中的解释器。

## 1. 先理解边界

这个流程可以回答“模型能否从离线好坏答案对中进一步改进”，但它没有 CARLA
环境状态、碰撞反馈或新轨迹采样，所以属于离线偏好优化数据飞轮，不是环境闭环
强化学习。chosen 来自 nuScenes ego pose 生成的标签，rejected 来自冻结 SFT。

最终 `val.jsonl` 只能用于最后评估，不能参与候选生成。脚本同时检查 sample ID
和 scene token，只要有一种重叠就停止。

## 2. 合并 v5 SFT

直接加载一个 4bit policy 和另一个 4bit reference 会让 RTX 5090 32 GB OOM。
因此先把 v5 SFT LoRA 合并到 bf16 基座：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/llamafactory-cli export \
  configs/qwen3vl_8b_merge_v5_history_sft.yaml
```

DPO 时只加载合并后的 SFT 和一个新的 LoRA。LLaMA-Factory 计算 reference
log-prob 时禁用新 LoRA，得到的 reference 正是冻结 SFT。DPO 评估时也必须用
这个合并模型做 baseline，避免把合并后再量化的数值差异算成 DPO 收益。

## 3. 构造 4000 条候选

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/sample_dpo_candidates.py \
  --source-path data/nuscenes_vla_sft_trainval_v5_history/train.jsonl \
  --forbidden-data-path data/nuscenes_vla_sft_trainval_v5_history/val.jsonl \
  --output-path data/drivevla_dpo/candidates.jsonl \
  --report-path data/drivevla_dpo/candidate_report.json \
  --max-samples 4000
```

默认动作比例为 KEEP_LANE 20%、SLOW_DOWN 30%、STOP 10%、TURN_LEFT 20%、
TURN_RIGHT 20%，并且不复制样本。

用冻结的合并 SFT 生成 rejected：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/infer_drivevla.py \
  --model-name-or-path results/qwen3vl_8b_drivevla_v5_history_sft_merged \
  --data-path data/drivevla_dpo/candidates.jsonl \
  --model-label qlora_v5_sft_merged \
  --output-path results/dpo_candidate_predictions.jsonl \
  --max-new-tokens 192 --image-max-pixels 196608 \
  --batch-size 2 --resume
```

`--resume` 会跳过已写入的 sample ID，中断后可以原命令续跑。

## 4. 构造单字段偏好对

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/build_dpo_preferences.py \
  --source-data-path data/drivevla_dpo/candidates.jsonl \
  --predictions-path results/dpo_candidate_predictions.jsonl \
  --forbidden-data-path data/nuscenes_vla_sft_trainval_v5_history/val.jsonl \
  --output-dir data/drivevla_dpo/preferences_isolated \
  --rejected-mode isolated_error \
  --min-margin 0.10 --max-pairs 3200 \
  --max-per-category-json \
  '{"slow_keep_confusion":500,"stop_confusion":400,"turn_action_error":500,"other_action_error":300,"turn_geometry":800,"trajectory_error":1000,"invalid_output":200}' \
  --val-ratio 0.10 --seed 42
```

`isolated_error` 的含义：

- 动作错误 pair 只把 rejected 的 `action` 换成 SFT 错误动作；
- 轨迹错误 pair 只把 rejected 的 `trajectory` 换成 SFT 预测轨迹；
- risk-only 默认不使用，因为 Risk 是 heuristic 弱标签；
- 无法解析的输出保留整段原始 rejected。

构建后必须查看 `preference_report.md`，确认图片存在、scene overlap 为 0，并
检查某个失败类别或 GT action 是否占据大多数。类别上限是安全阀，不足的类别
不会通过复制补齐。

注册数据：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/register_dpo_dataset.py \
  --source-dir data/drivevla_dpo/preferences_isolated \
  --dataset-prefix drivevla_v5_dpo
```

## 5. 训练

先用 `configs/qwen3vl_8b_qlora_dpo_smoke.yaml` 完成 2 step 冒烟。正式
isolated-DPO 配置为：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/llamafactory-cli train \
  configs/qwen3vl_8b_qlora_dpo_full_isolated.yaml
```

当前配置为 NF4 4bit、bf16、LoRA rank 16、batch size 1、梯度累积 8、
学习率 `5e-6`、1 epoch、DPO beta `0.1`。DPO adapter 的基座必须是合并后的
v5 SFT，推理时不能再叠加原 v5 adapter。

## 6. 公平评估

先在最终验证集前 200 条做门槛测试。SFT baseline：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/infer_drivevla.py \
  --model-name-or-path results/qwen3vl_8b_drivevla_v5_history_sft_merged \
  --data-path data/nuscenes_vla_sft_trainval_v5_history/val.jsonl \
  --model-label qlora_v5_sft_merged \
  --output-path results/dpo_val200_sft_predictions.jsonl \
  --max-new-tokens 192 --max-samples 200 \
  --image-max-pixels 196608 --batch-size 2 --resume
```

DPO candidate 使用完全相同参数，只增加：

```text
--adapter-path results/qwen3vl_8b_drivevla_v5_dpo_full_isolated
--model-label qlora_v5_dpo_full_isolated
--output-path results/dpo_val200_predictions.jsonl
```

一键后处理：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/process_dpo_results.py \
  --baseline-path results/dpo_val200_sft_predictions.jsonl \
  --candidate-path results/dpo_val200_predictions.jsonl \
  --output-dir results --prefix dpo_val200
```

脚本会严格检查两组 sample ID，并输出 Parse Success、Action/Risk Accuracy、
ADE/FDE、分动作 F1、混淆矩阵、成对 ADE 胜负和轨迹几何报告。

放大到 2115 条验证集前，200 条 pilot 必须同时满足：

- Parse Success 和 Trajectory Valid 不下降；
- Action Accuracy、ADE、FDE 均不退化；
- SLOW_DOWN 或转弯子集至少一项有明确改善；
- 不能只依据 preference accuracy 或 eval loss 宣称有效。

## 7. 已运行结果

两轮 336 train / 36 val 的 1 epoch pilot 已真实完成：

| Model | Preference Acc | Action Acc | ADE | FDE |
|---|---:|---:|---:|---:|
| merged SFT | - | 64.00% | 0.8371 | 1.8579 |
| full-output rejected | 97.22% | 63.50% | 0.8439 | 1.8895 |
| isolated-field rejected | 94.44% | 64.00% | 0.8477 | 1.8797 |

两版都未通过放大门槛，所以目前不运行全量 DPO，也不替换 v5 SFT。详细结果见
[`results/dpo_pilot_summary.md`](../results/dpo_pilot_summary.md)。
