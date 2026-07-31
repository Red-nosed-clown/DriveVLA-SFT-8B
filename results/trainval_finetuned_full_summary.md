# Trainval QLoRA 完整验证集评估摘要

## 评估设置

- 模型：`Qwen/Qwen3-VL-8B-Instruct`
- Adapter：`results/qwen3vl_8b_drivevla_trainval_qlora`
- 验证集：`data/nuscenes_vla_sft_trainval/val.jsonl`
- 样本数：2319
- 相机：`CAM_FRONT`
- 轨迹点：未来 6 个 `[forward_m, lateral_m]`

## 整体指标

| Metric | Value |
|---|---:|
| Parse Success | 99.83% |
| Action Accuracy | 80.42% |
| Risk Accuracy | 95.34% |
| Trajectory Valid | 99.83% |
| ADE | 2.2574 m |
| FDE | 3.9219 m |

## 动作分布

| Action | Ground Truth | Prediction |
|---|---:|---:|
| KEEP_LANE | 1348 | 1447 |
| TURN_LEFT | 284 | 251 |
| TURN_RIGHT | 257 | 274 |
| SLOW_DOWN | 63 | 48 |
| STOP | 367 | 296 |
| UNKNOWN | 0 | 3 |

## 动作混淆矩阵

| GT \ Pred | KEEP_LANE | TURN_LEFT | TURN_RIGHT | SLOW_DOWN | STOP | UNKNOWN |
|---|---:|---:|---:|---:|---:|---:|
| KEEP_LANE | 1220 | 50 | 51 | 18 | 6 | 3 |
| TURN_LEFT | 72 | 193 | 18 | 1 | 0 | 0 |
| TURN_RIGHT | 65 | 5 | 184 | 2 | 1 | 0 |
| SLOW_DOWN | 20 | 3 | 3 | 8 | 29 | 0 |
| STOP | 70 | 0 | 18 | 19 | 260 | 0 |

## 分动作准确率

| Action | Correct / Total | Accuracy |
|---|---:|---:|
| KEEP_LANE | 1220 / 1348 | 90.50% |
| TURN_LEFT | 193 / 284 | 67.96% |
| TURN_RIGHT | 184 / 257 | 71.60% |
| SLOW_DOWN | 8 / 63 | 12.70% |
| STOP | 260 / 367 | 70.84% |

## 结论

- trainval 训练后，模型已经不再塌缩到 `KEEP_LANE` / `STOP`，能够稳定预测 `TURN_LEFT` 和 `TURN_RIGHT`。
- 主要短板是 `SLOW_DOWN`，63 个真值样本里只预测对 8 个，很多被预测成 `STOP` 或 `KEEP_LANE`。
- `STOP` 也有一定漏检，367 个真值样本里 70 个被预测成 `KEEP_LANE`。
- 后续优化优先级应是：增强 `SLOW_DOWN` / `STOP` 的标签定义和样本均衡，其次再考虑多相机输入。
