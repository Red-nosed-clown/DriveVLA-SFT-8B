# VERL GRPO 教学型闭环

本阶段直接从 v6 SFT adapter 出发，用 VERL 在离线 nuScenes 样本上完成一次
`rollout -> reward -> advantage -> LoRA update -> weight sync`。它验证后训练工程链路，
不把离线规则奖励描述成 CARLA 在线环境奖励，也不替代完整泛化评估。

## 1. 数据转换

```bash
/home/pc/miniconda3/envs/drivevla_verl/bin/python \
  scripts/build_verl_drivevla_dataset.py
```

默认从 v6 JSONL 选择 16 条训练样本和 8 条验证样本，输出到
`data/drivevla_verl/smoke`。prompt 只包含当前图像、历史自车运动和当前可见目标，
ground truth 只放在 reward 使用的 `reward_model.ground_truth` 中，避免答案泄漏。
smoke 将图像上限设为 65,536 像素，只用于单卡链路验证。

## 2. 奖励设计

[`scripts/drivevla_verl_reward.py`](../scripts/drivevla_verl_reward.py) 将总奖励拆为：

| 分量 | 权重 |
|---|---:|
| JSON 格式 | 0.15 |
| Action | 0.10 |
| Risk | 0.05 |
| ADE | 0.25 |
| FDE | 0.15 |
| Target speed | 0.10 |
| 轨迹几何 | 0.10 |
| 动作/速度/风险一致性 | 0.10 |

额外惩罚错误停车、危险场景高速行驶、转向方向错误和无效轨迹。奖励是可解释的
离线代理目标，正式实验必须再与冻结验证集 ADE/FDE、速度 MAE 和 CARLA 安全指标对照。

## 3. 环境与兼容补丁

VERL 使用独立环境 `drivevla_verl`，避免改变已经稳定的 `drivevla_sft`。当前最新版
VERL 在 PyTorch 2.11 的视觉 mRoPE jagged tensor 和 FSDP2 分层 LoRA 同步上需要
三处小兼容修复：mRoPE jagged tensor 重建、动态 mRoPE 轴数，以及 FSDP2
分层 LoRA 权重同步：

```bash
bash scripts/apply_verl_compat_patch.sh
```

补丁内容保存在
[`patches/verl_qwen3vl_fsdp2_compat.patch`](../patches/verl_qwen3vl_fsdp2_compat.patch)，
不会把第三方 VERL 源码直接提交到本仓库。

## 4. 单步 smoke

```bash
bash scripts/run_verl_grpo_smoke.sh
```

脚本使用 v6 rank-16 adapter、GRPO `n=2`、batch size 1、SDPA、FSDP2、vLLM
共置和 CPU offload。RTX 5090 32GB + 64GB 主机内存的真实 smoke 已完成，退出码为 0：

- prompt token：539；总 token：1,293；
- rollout：8.16 秒；reward：小于 1 毫秒；
- actor update：11.27 秒；LoRA 权重同步：1.52 秒；
- 单步总耗时：20.96 秒；吞吐：61.69 token/s。

这些数字只说明端到端链路可运行，不是模型效果结论。下一阶段应先保存训练后的 adapter，
在固定 scene 验证集做 SFT/GRPO 配对评估，再决定是否扩展训练步数。

## 5. 8-step 短训与固定验证集

执行：

```bash
bash scripts/run_verl_grpo_short.sh
```

脚本完成 8 个 GRPO step，保存 8 份 rollout JSONL 和 LoRA-only FSDP checkpoint，
再导出标准 PEFT adapter。导出结果包含 504 个张量、43,646,976 个参数，大小约
87 MB。训练采样共 16 条，平均 reward 为 0.6583，但这不是冻结验证指标。

在相同 8 条 scene 隔离样本、相同 65,536 图像像素上进行 greedy 对照：

| Metric | v6 SFT | 8-step GRPO | GRPO - SFT |
|---|---:|---:|---:|
| Parse Success | 75.00% | 75.00% | 0.00% |
| Action Accuracy | 62.50% | 50.00% | -12.50% |
| Risk Accuracy | 75.00% | 75.00% | 0.00% |
| ADE | 0.9936 m | 0.8890 m | -0.1046 m |
| FDE | 2.1551 m | 1.9112 m | -0.2439 m |
| Target Speed MAE | 1.0500 m/s | 0.6450 m/s | -0.4050 m/s |

GRPO 改善了该小样本上的轨迹和速度误差，但 Action Accuracy 下降，逐样本 ADE 为
2 胜、2 平、4 负。该 adapter 因此只作为工程 pilot，不替代 v6 SFT。8 条样本也
不足以给出统计结论；下一轮应至少扩展到固定 100–200 条验证样本，并提高格式与
Action 奖励权重、降低学习率后再训练。
