# DriveVLA-SFT-8B

基于 `Qwen/Qwen3-VL-8B-Instruct + 4bit QLoRA` 的自动驾驶
Vision-Language-Action 微调项目。项目使用本地 `nuScenes-mini`，主训练由
LLaMA-Factory 完成，推理、输出解析、ADE/FDE、可视化和失败分析由项目自行实现。

## 项目动机

普通 VQA 只需要描述图像，本项目要求模型把视觉和语言条件转换为可评估的驾驶
Action、Risk 和连续轨迹。重点不是声称小数据模型可以直接控制车辆，而是完成
“数据构建、真实 8B QLoRA、结构化生成、离线指标、可视化和失败分析”的工程闭环。

## 任务定义

输入：

- `CAM_FRONT` 前视相机图像；
- 自然语言驾驶指令；
- 车辆、行人和障碍物等场景统计。

输出严格 JSON：

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [[4.51, -0.01], [9.32, 0.01], [13.52, 0.08], [17.59, 0.17], [21.07, 0.25], [24.82, 0.38]],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

`trajectory` 是当前自车坐标系下未来 6 个关键帧的
`[forward_m, lateral_m]`。Risk 来自交通参与者数量的 heuristic 弱监督，
不是 nuScenes 人工风险标注。

## 已构建数据

数据源：`/home/pc/datasets/nuscenes`

| Split | Samples | Scenes |
|---|---:|---:|
| Train | 310 | 9 |
| Validation | 34 | 1 |
| Total | 344 | 10 |

训练集和验证集按 scene 划分且无交集，scene 尾部不足 6 个未来帧的样本直接跳过。
六点未来轨迹的平均累计路程为 16.78 米。
完整分布见
[`data/nuscenes_vla_sft/dataset_report.md`](data/nuscenes_vla_sft/dataset_report.md)。

## 环境

所有命令使用 Conda 环境 `drivevla_sft`。当前验证环境：

- Python 3.10.20；
- PyTorch 2.12.0 + CUDA 13.0；
- Transformers 4.57.1；
- PEFT 0.17.1；
- bitsandbytes 0.49.2；
- RTX 5090 32 GB，支持 bf16。

先执行：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/check_environment.py
```

本机终端带有 Isaac Sim 的外部 `PYTHONPATH`，所以项目命令显式移除该变量，
防止错误导入其他 Conda 环境中的包。

项目内 LLaMA-Factory 固定到支持 Python 3.10 和 Qwen3-VL 的提交：

```bash
git clone https://github.com/hiyouga/LLaMA-Factory.git third_party/LLaMA-Factory
cd third_party/LLaMA-Factory
git checkout --detach b44f651e0905fed54f9455acd25bc2cfed8f1b94
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  -m pip install -e ".[torch,metrics]"
```

## 数据构建

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/convert_nuscenes_to_qwen3vl.py \
  --nuscenes_root /home/pc/datasets/nuscenes \
  --output_dir data/nuscenes_vla_sft \
  --train_ratio 0.9 \
  --future_steps 6 \
  --camera CAM_FRONT
```

注册到项目内的 LLaMA-Factory：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/register_llamafactory_dataset.py
```

## QLoRA 训练

先执行 32 条样本、2 step 的冒烟训练：

```bash
cd third_party/LLaMA-Factory
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  CONDA_DEFAULT_ENV=drivevla_sft \
  HF_HUB_DISABLE_XET=1 \
  TOKENIZERS_PARALLELISM=false \
  /home/pc/miniconda3/envs/drivevla_sft/bin/llamafactory-cli \
  train ../../configs/qwen3vl_8b_qlora_smoke.yaml
```

冒烟通过后运行正式 3 epoch：

```bash
cd third_party/LLaMA-Factory
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  CONDA_DEFAULT_ENV=drivevla_sft \
  HF_HUB_DISABLE_XET=1 \
  TOKENIZERS_PARALLELISM=false \
  /home/pc/miniconda3/envs/drivevla_sft/bin/llamafactory-cli \
  train ../../configs/qwen3vl_8b_qlora.yaml
```

正式配置使用 NF4 4bit、bf16、LoRA rank 16、batch size 1、梯度累积 8、
学习率 `1e-4` 和 3 epoch，并冻结视觉塔与多模态投影层。

本机真实训练结果：

- 可训练参数：43,646,976，占总参数 0.4954%；
- 117 个 optimizer step，训练耗时 345.7 秒；
- 最终 train loss：0.4039；
- 最终 eval loss：0.4186；
- 训练峰值显存约 24.7 GB。

另开终端可观察显存和利用率：

```bash
watch -n 1 nvidia-smi
```

训练成功的基本判断是：loss 能持续记录、输出目录包含
`adapter_config.json` 和 adapter 权重、训练进程正常结束，并且 adapter 能重新
加载生成结果。若 OOM，按顺序降低 `image_max_pixels`、`cutoff_len` 和
`lora_rank`，不要直接改成全参数训练。

## 自写评估

训练后分别对 base 和 adapter 运行：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/infer_drivevla.py --model-label base \
  --output-path results/predictions_base.jsonl

env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/infer_drivevla.py --model-label qlora \
  --adapter-path results/qwen3vl_8b_drivevla_qlora \
  --output-path results/predictions_finetuned.jsonl
```

评估链路包括：

- 严格 JSON、code fence、对象提取和旧格式正则四级解析；
- Parse Success、Action Accuracy、Risk Accuracy、Trajectory Valid；
- 六点轨迹 ADE 和 FDE；
- 失败案例分类、Markdown 报告和图像/轨迹可视化。

## 实验结果

以下结果来自同一组 34 条 scene 隔离验证样本、相同 4bit 推理和 greedy decoding：

| Model | Parse Success | Action Acc | Risk Acc | Trajectory Valid | ADE (m) | FDE (m) |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-VL-8B Base | 0.00% | 0.00% | 0.00% | 100.00% | 5.7259 | 9.7330 |
| Qwen3-VL-8B + QLoRA | 100.00% | 47.06% | 79.41% | 100.00% | 2.9181 | 5.5081 |

相对 Base，QLoRA 将 ADE 降低 49.04%，FDE 降低 43.41%。Base 能生成六点
数值轨迹，但 Action/Risk 使用中文自由文本而不是规定枚举，因此严格解析、
Action Accuracy 和 Risk Accuracy 均记为 0；这正是结构化 SFT 带来的核心改进。

完整结果见：

- [Base 与 QLoRA 对比](results/base_vs_qlora.md)
- [QLoRA 指标](results/finetuned_eval_report.md)
- [QLoRA 失败分析](results/finetuned_failure_analysis.md)

## 可视化

下图同时显示原始 `CAM_FRONT`、真实六点轨迹和 QLoRA 预测轨迹：

![DriveVLA trajectory example](results/figures/finetuned/019_acf9fcbeb1e346b98640f694f15460e8.png)

项目共生成 Base 与 QLoRA 各 20 张轨迹图。QLoRA 的主要失败模式是把验证集
中的 TURN_LEFT 预测为 KEEP_LANE 或 STOP；它在 10 个 TURN_LEFT 样本上没有
预测出 TURN_LEFT，说明 344 条小数据和动作不均衡仍不足以学习稳定转弯决策。

## 教学版训练

[`scripts/train_qwen_vl_lora_minimal.py`](scripts/train_qwen_vl_lora_minimal.py)
只支持小数据、单卡和 batch size 1，用于展示：

- processor 与 chat template；
- 图像和文本联合编码；
- assistant-only loss mask；
- NF4 4bit 基座加载；
- LoRA adapter 挂载与保存。

它用于解释原理，不替代 LLaMA-Factory 的正式训练结果。
该脚本已用 2 条真实样本、1 个 optimizer step 完成 QLoRA 冒烟验证并成功保存
adapter。

## 文档

- [数据构建](docs/01_dataset.md)
- [QLoRA 微调](docs/02_qlora_finetuning.md)
- [自写评估](docs/03_evaluation.md)
- [失败分析](docs/04_failure_analysis.md)

## 项目边界

nuScenes-mini 只有 10 个 scene，当前结果用于验证完整工程链路，不代表真实道路
泛化或闭环控制性能。9:1 scene 划分后的单个验证 scene 不包含 STOP、
TURN_RIGHT 和 LOW risk，分类结果不能代表这些类别的验证性能。第一版仅使用
单目 `CAM_FRONT`，也没有车辆控制器和仿真闭环。

## 后续方向

- 扩展到完整 nuScenes trainval，并保证 scene 级验证集覆盖所有动作类别；
- 对 TURN_LEFT、TURN_RIGHT 和 SLOW_DOWN 做重采样或类别加权；
- 从单前视图扩展到六视图；
- 接入 CARLA 或规划控制器，补充碰撞率、到达率和闭环轨迹偏差。

## 简历描述

- 基于 nuScenes-mini 前视图像、ego pose 与目标标注构建 344 条 VLA SFT
  数据，将未来 6 个 ego pose 转换到当前自车坐标系，并按 scene 隔离训练/验证集。
- 在单卡 RTX 5090 上使用 NF4 4bit QLoRA 微调 Qwen3-VL-8B-Instruct，仅训练
  0.4954% 参数，实现 Action、heuristic Risk、六点轨迹和 Reason 的结构化生成。
- 自行实现多级 JSON 容错解析、Action/Risk Accuracy、ADE/FDE、轨迹可视化与
  失败分析；相较 Base，Parse Success 从 0% 提升至 100%，ADE 降低 49.04%。
