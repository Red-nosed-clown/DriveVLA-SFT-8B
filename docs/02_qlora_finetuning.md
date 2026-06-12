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

## 真实训练结果

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

## 教学版脚本

`scripts/train_qwen_vl_lora_minimal.py` 展示 processor、chat template、
assistant-only loss mask、NF4 加载和 adapter 保存。它只面向小数据和
batch size 1，不用于替代正式训练。

教学脚本已使用 2 条真实样本和 1 step 运行验证，能够正常反向传播并保存
21,823,488 个 rank 8 LoRA 可训练参数。
