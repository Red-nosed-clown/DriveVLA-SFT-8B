# QLoRA 微调

## 主训练路线

正式结果使用 LLaMA-Factory。项目固定使用兼容 Python 3.10 且支持 Qwen3-VL
的 LLaMA-Factory 提交：

```text
b44f651e0905fed54f9455acd25bc2cfed8f1b94
```

核心配置：

- 基座：`Qwen/Qwen3-VL-8B-Instruct`；
- 量化：bitsandbytes NF4 4bit；
- 计算精度：bf16；
- LoRA rank 16、alpha 32；
- 单卡 batch size 1、梯度累积 8；
- 学习率 `1e-4`，训练 3 epoch；
- 冻结视觉塔和多模态投影层。

4bit 量化降低冻结基座权重的显存占用，LoRA 只学习少量低秩矩阵。两者组合后，
32 GB 单卡可以完成 8B 多模态模型的参数高效微调。

## 数据注册

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/register_llamafactory_dataset.py
```

注册脚本使用 JSON 解析器更新 `dataset_info.json`，不会用字符串拼接破坏原文件。

## 冒烟训练

完整训练前先用 32 条样本和 2 个 optimizer step 检查：

```bash
cd third_party/LLaMA-Factory
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  CONDA_DEFAULT_ENV=drivevla_sft \
  HF_HUB_DISABLE_XET=1 \
  TOKENIZERS_PARALLELISM=false \
  /home/pc/miniconda3/envs/drivevla_sft/bin/llamafactory-cli \
  train ../../configs/qwen3vl_8b_qlora_smoke.yaml
```

## 正式训练

```bash
cd third_party/LLaMA-Factory
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  CONDA_DEFAULT_ENV=drivevla_sft \
  HF_HUB_DISABLE_XET=1 \
  TOKENIZERS_PARALLELISM=false \
  /home/pc/miniconda3/envs/drivevla_sft/bin/llamafactory-cli \
  train ../../configs/qwen3vl_8b_qlora.yaml
```

本机终端继承了 Isaac Sim 的 `PYTHONPATH`，所以命令显式使用
`env -u PYTHONPATH`，避免错误导入外部环境中的包。

## nuScenes-mini 真实训练结果

- 训练样本 310，验证样本 34；
- 3 epoch，共 117 个 optimizer step；
- 可训练参数 43,646,976，占总参数 0.4954%；
- 训练耗时 345.7 秒；
- 最终 train loss 0.4039；
- 最终 eval loss 0.4186；
- 实测峰值显存约 24.7 GB。

验证 loss 在 step 20/40/60/80/100 分别为
`0.5031 / 0.4414 / 0.4244 / 0.4209 / 0.4227`，最终完整评估为 0.4186。
训练输出包含最终 adapter、两个最近 checkpoint、loss 曲线和 trainer 日志。

## Trainval 真实训练结果

第二阶段使用本地完整 trainval 相机数据重新构建数据集：

- 数据目录：`/home/pc/datasets/Full_dataest`；
- 输出目录：`data/nuscenes_vla_sft_trainval`；
- 总样本：23349；
- 训练样本：21030；
- 验证样本：2319；
- 划分方式：按 scene 划分，训练集和验证集 scene 无交集。

正式 QLoRA 训练仍使用 `Qwen/Qwen3-VL-8B-Instruct`、NF4 4bit、bf16、LoRA
rank 16、batch size 1、梯度累积 8、学习率 `1e-4` 和 3 epoch。

本次完整训练结果：

- 3 epoch，共 7887 个 optimizer step；
- 训练耗时约 6 小时 54 分钟；
- 最终 train loss：0.3218；
- 最终 eval loss：0.3380；
- adapter 输出目录：`results/qwen3vl_8b_drivevla_trainval_qlora`。

完整验证集评估显示动作准确率提升到 80.42%，但轨迹几何分析发现预测轨迹仍偏直、
偏平滑。这个结果说明训练已经学到多类动作和输出协议，但连续轨迹形状还需要通过
标签、采样、历史状态或多相机信息继续优化。

## Trainval v2 冒烟训练

针对“预测轨迹偏直”和 `SLOW_DOWN` 弱的问题，v2 数据转换增加了两项改动：

- `--action-rule v2`：动作标签不再只看未来终点，还会参考累计路程、平均步长、
  最后一段位移和速度变化趋势；
- `--balance-train`：只对训练集做动作均衡采样，验证集保持真实 scene 分布。

v2 数据统计：

- 总样本：23349；
- 原始训练样本：21030；
- 均衡后训练样本：19135；
- 验证样本：2319；
- 均衡后训练集每类 action 都是 3827 条；
- 验证集 action 分布：KEEP_LANE 1107、TURN_LEFT 242、TURN_RIGHT 235、
  SLOW_DOWN 360、STOP 375。

v2 冒烟训练已通过：

- 配置：`configs/qwen3vl_8b_qlora_trainval_v2_smoke.yaml`；
- 训练方式：Qwen3-VL 8B、4bit QLoRA、bf16、LoRA rank 8、2 step；
- 可训练参数：21,823,488；
- train loss：1.491；
- 输出目录：`results/qwen3vl_8b_drivevla_trainval_v2_smoke`。

注意：当前机器上直接调用 `llamafactory-cli train ...` 时，曾在参数解析阶段误报
`Your setup doesn't support bf16/gpu`。已验证同一 conda Python 直接调用
LLaMA-Factory `run_exp` 可以正常识别 `cuda:0` 和 bf16。v2 短训练建议使用：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python -c \
  "import yaml; from llamafactory.train.tuner import run_exp; cfg=yaml.safe_load(open('configs/qwen3vl_8b_qlora_trainval_v2_short.yaml', encoding='utf-8')); run_exp(cfg)"
```

这仍然是在 `drivevla_sft` 环境中使用 LLaMA-Factory 训练，只是绕过了本机当前
`llamafactory-cli` 包装入口的 CUDA 判断问题。

## Trainval v3 冒烟训练

v2 1000 step 短训练后发现强均衡采样效果不好：动作准确率下降，预测轨迹也更直。
因此 v3 只保留 `--action-rule v2`，去掉 `--balance-train`，用于单独验证动作弱
标签规则是否有帮助。

v3 数据统计：

- 输出目录：`data/nuscenes_vla_sft_trainval_v3_nobalance`；
- 总样本：23349；
- 训练样本：21030；
- 验证样本：2319；
- 训练集 action 分布：KEEP_LANE 9915、TURN_LEFT 1604、TURN_RIGHT 2194、
  SLOW_DOWN 3490、STOP 3827。

v3 冒烟训练已通过：

- 配置：`configs/qwen3vl_8b_qlora_trainval_v3_nobalance_smoke.yaml`；
- 训练方式：Qwen3-VL 8B、4bit QLoRA、bf16、LoRA rank 8、2 step；
- 可训练参数：21,823,488；
- train loss：1.4403；
- 输出目录：`results/qwen3vl_8b_drivevla_trainval_v3_nobalance_smoke`。

v3 1000 step 短训练配置为
`configs/qwen3vl_8b_qlora_trainval_v3_nobalance_short.yaml`。

## Trainval v4 冒烟训练

v3 1000 step 短训练后，Action Acc 回到 70.50%，ADE/FDE 也接近 v1，
但预测轨迹更保守：前 200 条验证样本中，预测近似直线比例达到 73.50%，
并且没有预测出 `SLOW_DOWN`。因此 v4 采用温和采样，而不是 v2 那种每类完全
均衡：

- 继续使用 `--action-rule v2`；
- 保留全部 KEEP_LANE 和 STOP；
- 将 `SLOW_DOWN` 采样到 7000 条；
- 将 `TURN_LEFT` 和 `TURN_RIGHT` 分别采样到 3000 条；
- 验证集仍然保持真实 scene split 分布。

v4 数据统计：

- 输出目录：`data/nuscenes_vla_sft_trainval_v4_mildsample`；
- 总样本：23349；
- 采样后训练样本：26742；
- 验证样本：2319；
- 训练集 action 分布：KEEP_LANE 9915、TURN_LEFT 3000、TURN_RIGHT 3000、
  SLOW_DOWN 7000、STOP 3827。

v4 冒烟训练已通过：

- 配置：`configs/qwen3vl_8b_qlora_trainval_v4_mildsample_smoke.yaml`；
- 训练方式：Qwen3-VL 8B、4bit QLoRA、bf16、LoRA rank 8、2 step；
- 可训练参数：21,823,488；
- train loss：1.4389；
- 输出目录：`results/qwen3vl_8b_drivevla_trainval_v4_mildsample_smoke`。

v4 1000 step 短训练配置为
`configs/qwen3vl_8b_qlora_trainval_v4_mildsample_short.yaml`。短训练完成后，
先评估前 200 条验证样本，重点看 `SLOW_DOWN` 是否开始被预测、ADE/FDE 是否
不劣于 v3，以及预测近似直线比例是否从 73.50% 降下来。

## Trainval v5 冒烟训练

v4 证明“只靠采样”不够：模型更敢输出 `SLOW_DOWN`，但会把不少 KEEP_LANE
误判为 SLOW_DOWN。v5 因此不再继续调采样，而是在 prompt 中加入历史 ego motion：

- `history_speed_mps`：过去 3 段关键帧速度；
- `current_speed_mps`：当前附近速度；
- `history_accel_mps2`：过去速度变化趋势；
- `history_yaw_delta_deg`：过去约 1.5 秒航向变化；
- `history_forward_delta_m` / `history_lateral_delta_m`：过去净位移。

这些字段只来自当前帧之前的 ego pose，不包含未来答案。它们的作用是让模型看到
“正在加速、匀速、减速、转向”的运动状态，而不是只凭单张前视图像猜。

v5 数据统计：

- 输出目录：`data/nuscenes_vla_sft_trainval_v5_history`；
- 总样本：21297；
- 训练样本：19182；
- 验证样本：2115；
- 训练集 action 分布：KEEP_LANE 7991、TURN_LEFT 1447、TURN_RIGHT 1987、
  SLOW_DOWN 4264、STOP 3493；
- scene 开头历史帧不足：2550。

v5 冒烟训练已通过：

- 配置：`configs/qwen3vl_8b_qlora_trainval_v5_history_smoke.yaml`；
- 训练方式：Qwen3-VL 8B、4bit QLoRA、bf16、LoRA rank 8、2 step；
- 可训练参数：21,823,488；
- train loss：1.3777；
- 输出目录：`results/qwen3vl_8b_drivevla_trainval_v5_history_smoke`。

v5 1000 step 短训练配置为
`configs/qwen3vl_8b_qlora_trainval_v5_history_short.yaml`。短训练完成后，
先评估前 200 条验证样本，重点判断历史运动是否减少 SLOW_DOWN 假阳性、是否提高
轨迹弯曲度，以及 ADE/FDE 是否不劣于 v3/v4。

## 教学版脚本

`scripts/train_qwen_vl_lora_minimal.py` 展示 processor、chat template、
assistant-only loss mask、NF4 加载和 adapter 保存。它只面向小数据和
batch size 1，不用于替代正式训练。

教学脚本已使用 2 条真实样本和 1 step 运行验证，能够正常反向传播并保存
21,823,488 个 rank 8 LoRA 可训练参数。
