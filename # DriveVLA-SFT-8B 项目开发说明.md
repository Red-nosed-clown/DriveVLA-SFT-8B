# DriveVLA-SFT-8B 项目开发说明

## 0. 项目目标

我要重新开始做一个秋招可展示的 VLA 实战项目，项目名暂定为：

```text
DriveVLA-SFT-8B
```

完整名称：

```text
DriveVLA-SFT-8B: QLoRA Fine-tuning Qwen3-VL-8B for Vision-Language-Action Autonomous Driving
```

中文定位：

```text
基于 Qwen3-VL-8B 的自动驾驶 Vision-Language-Action 指令微调项目
```

项目目标不是复现某个旧的第三方 DriveVLM 仓库，而是自己完成一个真实的大模型微调项目：

```text
输入：
- 自动驾驶前视图像
- 自然语言驾驶指令
- 场景统计信息，例如车辆数、行人数、障碍物数

输出：
- Action token，例如 KEEP_LANE / TURN_LEFT / SLOW_DOWN
- Risk level，例如 LOW / MEDIUM / HIGH
- Future trajectory，未来 6 个轨迹点
- Reason，简短驾驶解释
```

本项目要实现完整流程。训练主线先使用 LLaMA-Factory 跑通 Qwen3-VL-8B QLoRA，评估、解析和可视化链路自己实现；项目后期再补一个教学版 minimal 训练脚本，用于证明自己理解 LoRA/QLoRA 的核心原理。

```text
本地 nuScenes-mini 数据转换 → LLaMA-Factory Qwen3-VL-8B QLoRA 微调 → 推理 → 自写输出解析 → 自写 ADE/FDE 评估 → 自写可视化 → README 项目包装 → 教学版 minimal train 脚本
```

---

## 1. 重要背景

主线数据集使用本地 nuScenes-mini，路径为：

```text
/home/pc/datasets/nuscenes
```

其中元数据在：

```text
/home/pc/datasets/nuscenes/v1.0-mini
```

图像在：

```text
/home/pc/datasets/nuscenes/samples/CAM_FRONT
```

之前做过的 Mini-DriveVLA JSONL 只作为可选兼容输入，不作为第一阶段主线。旧格式大概是：

```json
{
  "image": "path/to/image.jpg",
  "instruction": "go straight",
  "future_trajectory": [[1.2, 0.0], [2.4, 0.1], [3.6, 0.1], [4.8, 0.2], [6.0, 0.2], [7.2, 0.2]],
  "vehicle_count": 13,
  "pedestrian_count": 30,
  "obstacle_count": 25,
  "sample_index": 0,
  "sample_token": "xxx"
}
```

如果后续需要兼容旧 Mini-DriveVLA JSONL，字段名不完全一致时，请让代码尽量兼容：

```text
instruction / command
future_trajectory / trajectory
vehicle_count / vehicles
pedestrian_count / pedestrians
obstacle_count / obstacles
```

如果没有某个字段，请给默认值并打印 warning，不要直接崩溃。

---

## 2. 硬件与训练路线

我的机器有一块 RTX 5090，显存 32GB。

项目直接做第三版：

```text
Qwen3-VL-8B-Instruct + 4bit QLoRA
```

不要先做 3B，不要训练小模型，不要做全参数微调。

技术栈建议：

```text
Python 3.10
PyTorch CUDA 12.8
Transformers
PEFT
bitsandbytes
qwen-vl-utils
LLaMA-Factory
matplotlib
numpy
pandas
Pillow
tqdm
```

训练方式：

```text
使用 LLaMA-Factory 启动 Qwen3-VL-8B-Instruct 的 QLoRA SFT
```

---

## 3. 项目目录结构

请创建或整理成如下结构：

```text
DriveVLA-SFT-8B/
├── README.md
├── requirements.txt
├── configs/
│   └── qwen3vl_8b_qlora.yaml
├── data/
│   ├── raw/                  # 可选：兼容旧 Mini-DriveVLA JSONL
│   ├── images/               # 可选：需要发布相对路径数据时再复制图片
│   ├── drivevla_train.json
│   ├── drivevla_val.json
│   └── dataset_report.md
├── scripts/
│   ├── convert_nuscenes_to_qwen3vl.py
│   ├── infer_drivevla.py
│   ├── parse_outputs.py
│   ├── evaluate_drivevla.py
│   ├── visualize_trajectory.py
│   ├── train_qwen_vl_lora_minimal.py
│   └── check_environment.py
├── results/
│   ├── predictions_base.jsonl
│   ├── predictions_finetuned.jsonl
│   ├── eval_metrics.json
│   ├── eval_report.md
│   └── figures/
├── docs/
│   ├── 01_dataset.md
│   ├── 02_qlora_finetuning.md
│   ├── 03_evaluation.md
│   └── 04_failure_analysis.md
└── third_party/
    └── LLaMA-Factory/
```

---

## 4. 第一阶段：环境检查脚本

请先写：

```text
scripts/check_environment.py
```

功能：

1. 检查 Python 版本。
2. 检查 torch 是否安装。
3. 检查 CUDA 是否可用。
4. 打印 GPU 名称。
5. 打印 CUDA capability。
6. 检查 transformers、peft、bitsandbytes、qwen_vl_utils 是否可以 import。
7. 如果 CUDA 不可用，给出清晰错误提示。

要求代码注释非常清楚，适合初学者阅读。每个函数都要说明：

```text
函数作用
输入
输出
为什么这样做
```

---

## 5. 第二阶段：本地 nuScenes-mini 数据转换脚本

请写：

```text
scripts/convert_nuscenes_to_qwen3vl.py
```

作用：

把本地 nuScenes-mini 原始数据转换成 Qwen3-VL / LLaMA-Factory 可用的多模态对话格式。不要依赖旧 Mini-DriveVLA JSONL 作为主输入。

输入：

```bash
python scripts/convert_nuscenes_to_qwen3vl.py \
  --nuscenes_root /home/pc/datasets/nuscenes \
  --version v1.0-mini \
  --output_dir data \
  --train_ratio 0.9 \
  --future_steps 6 \
  --camera CAM_FRONT
```

输出：

```text
data/drivevla_train.json
data/drivevla_val.json
data/dataset_report.md
```

说明：

```text
第一版可以直接使用 nuScenes 原始图片绝对路径，不强制复制图片到 data/images。
如果后续为了发布项目需要相对路径，再增加 --copy_images 选项复制 CAM_FRONT 图片。
```

每条转换后的样本格式：

```json
{
  "messages": [
    {
      "role": "user",
      "content": "<image>You are an autonomous driving assistant.\nCommand: follow the road safely.\nScene statistics: vehicles=13, pedestrians=30, obstacles=25.\nPredict the driving action, risk level, and future trajectory of the ego vehicle.\nPlease answer in JSON format with keys: action, risk, trajectory, reason."
    },
    {
      "role": "assistant",
      "content": "{\"action\": \"KEEP_LANE\", \"risk\": \"MEDIUM\", \"trajectory\": [[1.2, 0.0], [2.4, 0.1], [3.6, 0.1], [4.8, 0.2], [6.0, 0.2], [7.2, 0.2]], \"reason\": \"The ego vehicle should keep lane while paying attention to nearby traffic participants.\"}"
    }
  ],
  "images": ["/home/pc/datasets/nuscenes/samples/CAM_FRONT/sample_xxx.jpg"]
}
```

### 5.1 nuScenes 轨迹标签生成

请实现函数：

```python
build_future_trajectory(current_pose, future_poses)
```

要求：

```text
1. 从 sample.json 根据 next 字段找到未来 future_steps 个关键帧。
2. 通过 sample_data.json 找到当前帧和未来帧对应的 CAM_FRONT key frame。
3. 通过 ego_pose_token 读取 ego_pose.json 中的自车位姿。
4. 将未来世界坐标位姿转换到当前自车坐标系。
5. 输出 [[forward_1, lateral_1], ..., [forward_6, lateral_6]]。
6. scene 末尾不足 future_steps 的样本，第一版直接跳过，避免补齐造成监督噪声。
```

注意：

```text
不能直接把 nuScenes 世界坐标 x/y 当成自车前向/横向。
必须先用当前 ego pose 的 yaw 做坐标变换。
```

### 5.2 Action token 规则

请实现函数：

```python
infer_action_token(future_trajectory)
```

规则先用简化版：

```text
如果 final_x < 1.0：
    STOP

如果 final_y > 1.0：
    TURN_LEFT

如果 final_y < -1.0：
    TURN_RIGHT

如果 final_x < 3.0：
    SLOW_DOWN

否则：
    KEEP_LANE
```

后续可以扩展：

```text
LANE_CHANGE_LEFT
LANE_CHANGE_RIGHT
ACCELERATE
```

但第一版先保证跑通。

### 5.3 Risk level 规则

请实现函数：

```python
infer_risk_level(vehicle_count, pedestrian_count, obstacle_count)
```

可以先用弱规则：

```text
score = vehicle_count * 0.05 + pedestrian_count * 0.08 + obstacle_count * 0.04

score >= 2.2 → HIGH
score >= 1.0 → MEDIUM
else → LOW
```

注意：

```text
Risk 是基于交通参与者数量的 heuristic 标签，不是真实人工风险标注。
README 和简历中要写清楚，避免夸大。
```

### 5.4 Trajectory 格式化

请实现函数：

```python
format_trajectory(traj, future_steps=6)
```

要求：

```text
1. 统一保留 6 个点
2. 如果不足 6 个点，用最后一个点补齐
3. 如果超过 6 个点，只取前 6 个
4. 每个坐标保留两位小数
```

### 5.5 数据报告

请自动生成：

```text
data/dataset_report.md
```

内容包括：

```text
总样本数
训练集样本数
验证集样本数
Action token 分布
Risk level 分布
平均轨迹长度
缺失图片数量
成功转换数量
失败样本数量
跳过的 scene 末尾不足 future_steps 样本数量
```

---

## 6. 第三阶段：LLaMA-Factory 数据注册

请写清楚操作说明，必要时写辅助脚本。

需要把数据复制到：

```text
third_party/LLaMA-Factory/data/
```

建议结构。第一版可以让 JSON 中的 `images` 字段使用 nuScenes 原始图片绝对路径；如果希望项目更容易迁移，再把图片复制到 `drivevla/images/` 并改成相对路径。

```text
third_party/LLaMA-Factory/data/
├── drivevla_train.json
├── drivevla_val.json
└── drivevla/                 # 可选：使用 --copy_images 时才需要
    └── images/
```

同时需要修改或自动更新：

```text
third_party/LLaMA-Factory/data/dataset_info.json
```

添加数据集信息：

```json
"drivevla_train": {
  "file_name": "drivevla_train.json",
  "formatting": "sharegpt",
  "columns": {
    "messages": "messages",
    "images": "images"
  },
  "tags": {
    "role_tag": "role",
    "content_tag": "content",
    "user_tag": "user",
    "assistant_tag": "assistant"
  }
}
```

如果 LLaMA-Factory 当前版本要求的字段有变化，请以当前仓库实际格式为准，并在 README 中说明。

---

## 7. 第四阶段：QLoRA 训练配置

请创建：

```text
configs/qwen3vl_8b_qlora.yaml
```

第一版配置建议：

```yaml
### model
model_name_or_path: Qwen/Qwen3-VL-8B-Instruct
template: qwen3_vl
trust_remote_code: true

### method
stage: sft
do_train: true
finetuning_type: lora
lora_rank: 16
lora_alpha: 32
lora_dropout: 0.05
lora_target: all

### quantization
quantization_bit: 4
quantization_method: bitsandbytes

### dataset
dataset: drivevla_train
cutoff_len: 1024
max_samples: 2000
overwrite_cache: true
preprocessing_num_workers: 4

### image
image_max_pixels: 262144

### output
output_dir: ../../results/qwen3vl_8b_drivevla_qlora
logging_steps: 1
save_steps: 50
plot_loss: true
overwrite_output_dir: true

### train
per_device_train_batch_size: 1
gradient_accumulation_steps: 8
learning_rate: 0.0001
num_train_epochs: 3
lr_scheduler_type: cosine
warmup_ratio: 0.03
bf16: true
fp16: false
gradient_checkpointing: true

### eval
val_size: 0.1
per_device_eval_batch_size: 1
eval_strategy: steps
eval_steps: 50

### misc
report_to: none
```

如果训练 OOM，优先修改：

```yaml
image_max_pixels: 131072
cutoff_len: 768
lora_rank: 8
gradient_accumulation_steps: 16
```

训练命令：

```bash
cd third_party/LLaMA-Factory
llamafactory-cli train ../../configs/qwen3vl_8b_qlora.yaml
```

请在 README 里写清楚：

```text
1. 如何安装 LLaMA-Factory
2. 如何注册数据集
3. 如何启动训练
4. 如何观察 nvidia-smi
5. 如何判断训练成功
6. OOM 怎么处理
```

---

## 8. 第五阶段：推理脚本

请写：

```text
scripts/infer_drivevla.py
```

功能：

1. 加载 Qwen3-VL-8B-Instruct 基座模型。
2. 支持加载 QLoRA adapter。
3. 对验证集进行批量推理。
4. 保存预测结果到 JSONL。

命令设计：

```bash
# 基座模型推理
python scripts/infer_drivevla.py \
  --model_name_or_path Qwen/Qwen3-VL-8B-Instruct \
  --data_path data/drivevla_val.json \
  --output_path results/predictions_base.jsonl \
  --max_new_tokens 256

# 微调模型推理
python scripts/infer_drivevla.py \
  --model_name_or_path Qwen/Qwen3-VL-8B-Instruct \
  --adapter_path results/qwen3vl_8b_drivevla_qlora \
  --data_path data/drivevla_val.json \
  --output_path results/predictions_finetuned.jsonl \
  --max_new_tokens 256
```

输出 JSONL 每行格式：

```json
{
  "sample_id": 0,
  "image": "data/images/sample_000001.jpg",
  "prompt": "...",
  "ground_truth": "{\"action\": \"KEEP_LANE\", \"risk\": \"MEDIUM\", \"trajectory\": ...}",
  "prediction": "{\"action\": \"KEEP_LANE\", \"risk\": \"LOW\", \"trajectory\": ...}",
  "gt_action": "KEEP_LANE",
  "gt_risk": "MEDIUM",
  "gt_trajectory": [[1.2, 0.0], [2.4, 0.1]]
}
```

注意：

```text
推理脚本要尽量兼容单张图片输入。
如果显存不足，先 batch size = 1。
推理时不要训练，不要保存梯度。
```

---

## 9. 第六阶段：输出解析脚本

请写：

```text
scripts/parse_outputs.py
```

功能：

从模型输出文本中解析：

```text
Action
Risk
Trajectory
Reason
```

要求：

1. 优先用 json.loads 解析。
2. 如果模型输出包含 markdown code block 或多余解释，先提取第一个 JSON 对象再解析。
3. JSON 解析失败时，再用正则表达式兜底解析。
4. 如果解析失败，不要崩溃。
5. 给出 parse_success 字段。
6. 轨迹解析失败时设为 None。
7. Action 不在合法集合中时设为 UNKNOWN。
8. Risk 不在合法集合中时设为 UNKNOWN。

合法 Action：

```python
VALID_ACTIONS = {
    "KEEP_LANE",
    "TURN_LEFT",
    "TURN_RIGHT",
    "SLOW_DOWN",
    "STOP",
    "LANE_CHANGE_LEFT",
    "LANE_CHANGE_RIGHT",
    "UNKNOWN"
}
```

合法 Risk：

```python
VALID_RISKS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "UNKNOWN"
}
```

---

## 10. 第七阶段：评估脚本

请写：

```text
scripts/evaluate_drivevla.py
```

输入：

```bash
python scripts/evaluate_drivevla.py \
  --pred_path results/predictions_finetuned.jsonl \
  --output_json results/eval_metrics.json \
  --output_md results/eval_report.md
```

评估指标：

```text
1. parse_success_rate
2. action_accuracy
3. risk_accuracy
4. ADE
5. FDE
6. trajectory_valid_rate
7. average_reason_length
```

ADE 定义：

```text
Average Displacement Error
预测轨迹每个时间点与真实轨迹的欧氏距离平均值
```

FDE 定义：

```text
Final Displacement Error
预测轨迹最后一个点与真实轨迹最后一个点的欧氏距离
```

同时输出 Markdown 报告：

```text
results/eval_report.md
```

报告包括：

```text
总体指标表格
Action 分类准确率
Risk 分类准确率
轨迹误差
解析失败样本数量
典型失败案例
```

---

## 11. 第八阶段：轨迹可视化

请写：

```text
scripts/visualize_trajectory.py
```

功能：

1. 从 predictions JSONL 中读取样本。
2. 画出 ground truth trajectory 和 predicted trajectory。
3. 如果能读取原图，可以在图旁边显示原始驾驶图像。
4. 保存到：

```text
results/figures/
```

命令：

```bash
python scripts/visualize_trajectory.py \
  --pred_path results/predictions_finetuned.jsonl \
  --output_dir results/figures \
  --num_samples 20
```

图中需要显示：

```text
Action GT / Pred
Risk GT / Pred
ADE / FDE
```

注意：

```text
matplotlib 不要强制指定花哨样式。
图要清楚，适合放进 README。
```

---

## 12. 第九阶段：README

请写完整 README.md，面向秋招项目展示。

README 结构：

```markdown
# DriveVLA-SFT-8B

## 1. Project Overview

## 2. Motivation

## 3. Vision-Language-Action Task Definition

## 4. Dataset Construction

## 5. Model and Fine-tuning Method

## 6. Training

## 7. Inference

## 8. Evaluation

## 9. Visualization

## 10. Results

## 11. Ablation / Comparison

## 12. Limitations

## 13. Future Work

## 14. Resume Description
```

README 里要突出：

```text
1. 这是真实 Qwen3-VL-8B QLoRA 微调，不是小模型训练。
2. 任务是自动驾驶 VLA，不是普通 VQA。
3. 输入是 image + language command。
4. 输出是 action + risk + trajectory + reason。
5. 有自动解析和 ADE/FDE 评估。
6. 有 base model vs fine-tuned model 对比。
```

---

## 13. 第十阶段：教学版 minimal LoRA/QLoRA 训练脚本

在 LLaMA-Factory 主线跑通以后，再补一个教学版本：

```text
scripts/train_qwen_vl_lora_minimal.py
```

定位：

```text
这个脚本不是为了替代 LLaMA-Factory，而是为了证明自己理解 Qwen3-VL 多模态 SFT、LoRA/QLoRA、collator、loss mask 和单卡训练的基本原理。
```

功能边界：

```text
1. 只支持小数据集。
2. 只支持单卡。
3. batch size 默认 1。
4. 支持 LoRA，尽量支持 QLoRA。
5. 只支持 Qwen3-VL-8B-Instruct。
6. 只做 SFT，不做复杂分布式训练。
7. 不追求完全复刻 LLaMA-Factory 的全部功能。
```

脚本要重点展示：

```text
1. AutoProcessor 如何处理 image + text。
2. apply_chat_template 如何构造多模态对话。
3. DataCollator 如何 padding。
4. 如何只对 assistant 输出计算 loss。
5. 如何给模型挂 LoRA adapter。
6. QLoRA 的 4bit BitsAndBytesConfig 如何配置。
7. 如何保存 adapter。
```

README 中要明确说明：

```text
主训练结果来自 LLaMA-Factory，minimal train 脚本用于教学和原理展示。
```

---

## 14. 第十一阶段：对比实验

至少做两个版本：

```text
Qwen3-VL-8B-Instruct base model
Qwen3-VL-8B-Instruct + DriveVLA QLoRA adapter
```

对比指标：

```text
parse_success_rate
action_accuracy
risk_accuracy
ADE
FDE
trajectory_valid_rate
```

输出表格示例：

```markdown
| Model | Parse Success | Action Acc | Risk Acc | ADE | FDE |
|---|---:|---:|---:|---:|---:|
| Qwen3-VL-8B Base | xx% | xx% | xx% | x.xx | x.xx |
| Qwen3-VL-8B + QLoRA | xx% | xx% | xx% | x.xx | x.xx |
```

---

## 15. 第十二阶段：失败案例分析

请生成：

```text
docs/04_failure_analysis.md
```

内容包括 失败案例：

```text
样本 ID
输入图像路径
指令
真实输出
模型预测输出
错误类型
可能原因
```

错误类型可以包括：

```text
Action error
Risk error
Trajectory parse failure
Large ADE
Large FDE
Invalid output format
```

---

## 16. 代码风格要求

非常重要：

我基础不太好，所以代码必须教学友好。

每个脚本要求：

```text
1. 文件开头写清楚这个脚本做什么。
2. 每个主要函数都要有 docstring。
3. docstring 要写：作用、输入、输出、为什么这样做。
4. 关键变量要有中文注释。
5. 尽量不要写太复杂的一行式代码。
6. 报错信息要清楚。
7. 路径参数必须用 argparse。
8. 读取 JSON/JSONL 要有异常处理。
9. 图片不存在时 warning，不要直接崩溃。
10. 输出目录不存在时自动创建。
```

---

## 17. requirements.txt

请生成一个基础版：

```text
torch
torchvision
torchaudio
transformers
accelerate
peft
bitsandbytes
qwen-vl-utils
datasets
trl
pillow
numpy
pandas
matplotlib
tqdm
scikit-learn
pyyaml
```

---

## 18. 推荐执行顺序

请按这个顺序生成和执行：

```bash
# 1. 建项目结构
mkdir -p data/raw data/images scripts configs results/figures docs third_party

# 2. 检查环境
python scripts/check_environment.py

# 3. 转换本地 nuScenes-mini 数据
python scripts/convert_nuscenes_to_qwen3vl.py \
  --nuscenes_root /home/pc/datasets/nuscenes \
  --version v1.0-mini \
  --output_dir data \
  --train_ratio 0.9 \
  --future_steps 6 \
  --camera CAM_FRONT

# 4. 安装并配置 LLaMA-Factory
cd third_party
git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e ".[torch,metrics]"
pip install -U qwen-vl-utils bitsandbytes peft accelerate transformers datasets trl

# 5. 注册数据集到 LLaMA-Factory
# 需要复制 data/drivevla_train.json、data/drivevla_val.json
# 如果 JSON 中使用绝对图片路径，可以先不复制 images
# 如果使用 --copy_images 生成相对图片路径，则同步复制 data/images
# 最后更新 dataset_info.json

# 6. 启动 QLoRA 训练
llamafactory-cli train ../../configs/qwen3vl_8b_qlora.yaml

# 7. 基座模型推理
python scripts/infer_drivevla.py \
  --model_name_or_path Qwen/Qwen3-VL-8B-Instruct \
  --data_path data/drivevla_val.json \
  --output_path results/predictions_base.jsonl

# 8. 微调模型推理
python scripts/infer_drivevla.py \
  --model_name_or_path Qwen/Qwen3-VL-8B-Instruct \
  --adapter_path results/qwen3vl_8b_drivevla_qlora \
  --data_path data/drivevla_val.json \
  --output_path results/predictions_finetuned.jsonl

# 9. 评估
python scripts/evaluate_drivevla.py \
  --pred_path results/predictions_finetuned.jsonl \
  --output_json results/eval_metrics.json \
  --output_md results/eval_report.md

# 10. 可视化
python scripts/visualize_trajectory.py \
  --pred_path results/predictions_finetuned.jsonl \
  --output_dir results/figures \
  --num_samples 20

# 11. 后期补教学版 minimal 训练脚本
python scripts/train_qwen_vl_lora_minimal.py \
  --train_path data/drivevla_train.json \
  --val_path data/drivevla_val.json \
  --output_dir results/minimal_lora_debug \
  --max_samples 32
```

---

## 19. 项目最终要能写进简历

请在 README 最后生成简历 bullet：

```text
DriveVLA-SFT-8B：基于 Qwen3-VL-8B 的自动驾驶 Vision-Language-Action 微调项目

- 构建 image-text-action 指令微调数据，将驾驶图像、导航指令、动作 token、风险等级与未来轨迹统一为多模态对话格式。
- 基于单卡 RTX 5090 使用 QLoRA 对 Qwen3-VL-8B-Instruct 进行参数高效微调，使模型能够根据驾驶图像和指令生成结构化驾驶动作、风险判断、未来轨迹和简短解释。
- 实现 VLA 输出解析与自动评估流程，统计 Action Accuracy、Risk Accuracy、ADE/FDE 和格式解析成功率，并对比基座模型与微调模型的输出稳定性。
- 设计动作 token 化规则和失败案例分析模块，完成预测轨迹可视化，分析视觉信息、语言指令和动作约束对驾驶决策生成的影响。
```

---

## 20. 注意事项

1. 不要把这个项目放进旧的第三方 DriveVLM 仓库。
2. 不要使用 CARLA 作为第一阶段主线。
3. 不要做全参数微调。
4. 直接按 Qwen3-VL-8B QLoRA 做。
5. 第一目标是跑通真实大模型微调链路。
6. 第二目标是完成自动评估和可视化。
7. 第三目标是 README 和简历包装。
8. 如果训练 OOM，先降低 image_max_pixels、cutoff_len、lora_rank。
9. 所有脚本都要适合初学者阅读，注释必须清楚。
10. 如果某一步无法自动完成，请在 README 里写清楚手动操作步骤。
11. 第一阶段训练主线使用 LLaMA-Factory，评估链路自己写。
12. 后期再补 minimal train 脚本，定位为教学和原理证明，不替代主训练框架。
