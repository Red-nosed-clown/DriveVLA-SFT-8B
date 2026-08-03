# v6 时序安全输入与目标速度监督

## 目标

v5 已加入 1.5 秒 ego 历史运动，但最近交通参与者仍只有单帧位置。单帧图像无法
稳定区分静止前车和慢速前车，因此 v6 增加以下可观测字段：

- 目标纵向速度；
- 目标相对纵向速度；
- ego 对目标的 closing speed；
- 仅对前方近车道目标计算的 TTC；
- assistant 额外预测 `target_speed_mps`。

nuScenes 目标运动只沿 `sample_annotation.prev` 读取过去标注，不使用未来目标
位置。`target_speed_mps` 由未来 ego 轨迹最后一段生成，只作为监督标签，不能
出现在输入 prompt 中。

## 已完成的数据构建

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/convert_nuscenes_to_qwen3vl.py \
  --nuscenes-root /home/pc/datasets/Full_dataest \
  --version v1.0-trainval \
  --output-dir data/nuscenes_vla_sft_trainval_v6_safety \
  --history-steps 3 \
  --action-rule v3 \
  --include-object-motion \
  --include-speed-target
```

真实转换结果：

- 训练样本：19,182；
- 验证样本：2,115；
- 最近目标：166,368 个；
- 可计算历史速度：164,267 个，覆盖率 98.74%；
- 可计算 TTC：12,268 个；
- 目标速度范围：0.00 到 16.19 m/s；
- 训练和验证 scene 无交集。

完整统计见
[`data/nuscenes_vla_sft_trainval_v6_safety/dataset_report.md`](../data/nuscenes_vla_sft_trainval_v6_safety/dataset_report.md)。

## 数据注册

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/register_llamafactory_dataset.py \
  --source-dir data/nuscenes_vla_sft_trainval_v6_safety \
  --llamafactory-dir third_party/LLaMA-Factory \
  --dataset-prefix drivevla_trainval_v6_safety
```

## 训练顺序

2-step QLoRA 冒烟已通过，train loss 为 1.2888。正式训练前仍应先确认 GPU 空闲：

```bash
nvidia-smi
```

正式训练命令：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  CONDA_DEFAULT_ENV=drivevla_sft \
  HF_HUB_OFFLINE=1 \
  TOKENIZERS_PARALLELISM=false \
  MPLCONFIGDIR=/tmp/drivevla_matplotlib \
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  /home/pc/miniconda3/envs/drivevla_sft/bin/llamafactory-cli train \
  configs/qwen3vl_8b_qlora_trainval_v6_safety_full.yaml
```

配置保持 4bit NF4、bf16、LoRA rank 16、batch size 1、梯度累积 8 和 3 epoch。

## 对照实验

正式结论至少包含以下对照，不能只报告 v6 单模型结果：

| Model | Ego history | Object motion/TTC | Target speed | DPO |
|---|---:|---:|---:|---:|
| v1 SFT | No | No | No | No |
| v5 SFT | Yes | No | No | No |
| v6 SFT | Yes | Yes | Yes | No |
| v6 DPO | Yes | Yes | Yes | Yes |

离线评估除 Action/Risk、ADE/FDE 和轨迹曲率外，还需报告 Target Speed Valid 与
Target Speed MAE。CARLA 配置中的 `planner.prompt_version` 只有在加载 v6 adapter
时才能改为 `v6_safety`；加载 v5 adapter 时必须保持 `v5`，避免输入分布错位。

## CARLA 指标

v6 在线观测使用 CARLA actor 当前速度计算同名字段，并新增：

- 每帧 `minimum_ttc_s`；
- episode 最小 TTC；
- TTC 有效观测数量；
- 模型预测目标速度经过控制器限幅后的实际目标速度。

STOP 始终覆盖模型目标速度并强制目标速度为 0；SLOW_DOWN 仍受控制器低速上限
约束。旧模型没有 `target_speed_mps` 时，控制器继续从六点轨迹估计速度。
