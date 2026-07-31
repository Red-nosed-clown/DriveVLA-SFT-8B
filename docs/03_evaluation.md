# 自写评估链路

## 评估流程

基座模型和 QLoRA adapter 使用同一验证集、同一生成参数分别推理：

```text
批量推理 -> 容错解析 -> 指标计算 -> 对比报告 -> 轨迹可视化
```

解析器依次尝试：

1. 直接解析严格 JSON；
2. 去掉 Markdown code fence；
3. 从混合文本提取第一个完整 JSON 对象；
4. 用正则兼容旧版四行文本。

任何单条解析失败都不会中断全量评估。

## 指标定义

- Parse Success：Action、Risk 和六点轨迹均可解析的比例。
- Action Accuracy：预测动作与标签一致的比例。
- Risk Accuracy：预测 heuristic risk 与弱监督标签一致的比例。
- Trajectory Valid：能得到 6 个有限二维点的比例。
- ADE：六个对应轨迹点欧氏距离的平均值。
- FDE：第六个轨迹点的欧氏距离。
- Trajectory Curvature：六点轨迹的二阶差分均值，用于判断轨迹是否过度直线化。
- Abs Final Lateral：最后一个轨迹点横向位移绝对值，用于观察转向幅度是否偏保守。

ADE/FDE 只在成功解析出有效六点轨迹的样本上计算，因此报告同时记录
`trajectory_metric_samples`，避免只看距离而忽略格式失败。

ADE/FDE 对轨迹形状不够敏感：如果模型输出一条平滑直线，只要整体距离接近 GT，
ADE/FDE 仍可能不差。因此 trainval 阶段新增
[`scripts/analyze_trajectory_geometry.py`](../scripts/analyze_trajectory_geometry.py)，
专门分析预测轨迹是否过度平滑或直线化。

## 命令模板

完成训练后，先运行 base 和 adapter 推理：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/infer_drivevla.py \
  --output-path results/predictions_base.jsonl \
  --model-label base

env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/infer_drivevla.py \
  --adapter-path results/qwen3vl_8b_drivevla_qlora \
  --output-path results/predictions_finetuned.jsonl \
  --model-label qlora
```

随后用 `parse_outputs.py`、`evaluate_drivevla.py` 和 `compare_metrics.py`
生成机器可读指标与 Markdown 对比报告。README 只填写这些命令真实运行后
得到的数值。

## 真实对比结果

| Model | Parse Success | Action Acc | Risk Acc | Trajectory Valid | ADE | FDE |
|---|---:|---:|---:|---:|---:|---:|
| Base | 0.00% | 0.00% | 0.00% | 100.00% | 5.7259 m | 9.7330 m |
| QLoRA | 100.00% | 47.06% | 79.41% | 100.00% | 2.9181 m | 5.5081 m |

Base 的 34 条输出都包含六点轨迹，但 Action/Risk 使用中文自由文本，不符合
规定枚举，因此严格 parse success 为 0。解析器仍保留其有效轨迹，所以能够
公平计算 ADE/FDE。QLoRA 将 ADE 降低 49.04%，FDE 降低 43.41%。

结果文件：

- `results/base_metrics.json`
- `results/finetuned_metrics.json`
- `results/base_vs_qlora.md`
- `results/predictions_base_parsed.jsonl`
- `results/predictions_finetuned_parsed.jsonl`

## Trainval 完整验证结果

第二阶段使用 `data/nuscenes_vla_sft_trainval/val.jsonl` 的 2319 条验证样本评估
trainval QLoRA adapter：

| Metric | Value |
|---|---:|
| Parse Success | 99.83% |
| Action Accuracy | 80.42% |
| Risk Accuracy | 95.34% |
| Trajectory Valid | 99.83% |
| ADE | 2.2574 m |
| FDE | 3.9219 m |

分动作准确率：

| Action | Correct / Total | Accuracy |
|---|---:|---:|
| KEEP_LANE | 1220 / 1348 | 90.50% |
| TURN_LEFT | 193 / 284 | 67.96% |
| TURN_RIGHT | 184 / 257 | 71.60% |
| SLOW_DOWN | 8 / 63 | 12.70% |
| STOP | 260 / 367 | 70.84% |

轨迹几何分析：

| Source | Mean Curvature | P50 | P90 | P99 |
|---|---:|---:|---:|---:|
| GT | 0.2023 | 0.1749 | 0.4142 | 0.7367 |
| Prediction | 0.1085 | 0.1004 | 0.2225 | 0.3735 |

结论是：trainval 训练解决了 mini 阶段的动作塌缩，模型已经能预测左右转；但预测
轨迹弯曲度只有 GT 的约一半，说明连续轨迹仍存在过度平滑和直线化。

结果文件：

- `results/trainval_finetuned_full_summary.md`
- `results/trainval_finetuned_full_eval_report.md`
- `results/trainval_finetuned_full_trajectory_geometry.md`
