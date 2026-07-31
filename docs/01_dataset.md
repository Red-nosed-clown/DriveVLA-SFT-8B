# 数据构建

## 数据来源

第一版只使用本机 `nuScenes-mini`：

```text
/home/pc/datasets/nuscenes
```

输入模态为 `CAM_FRONT` 前视图像，监督信号来自 nuScenes 的 ego pose 和
目标标注。Risk 是根据车辆、行人和障碍物数量生成的 heuristic 弱监督，
不是人工风险真值。

第二阶段扩展到本机 trainval 相机数据：

```text
/home/pc/datasets/Full_dataest
```

仍然只使用 `CAM_FRONT`。这样可以先把数据规模、训练链路和评估链路跑稳，再考虑
三前视相机或历史帧。

## 六点轨迹

对当前关键帧，脚本沿 `sample.next` 查找未来 6 个关键帧。每个未来世界坐标
点先减去当前 ego 世界坐标，再用当前 ego yaw 的逆旋转变换到当前自车坐标系：

```text
forward_m：当前车辆朝向的前方距离
lateral_m：当前车辆左侧为正的横向距离
```

scene 尾部不足 6 个未来关键帧时直接跳过，避免重复末点引入虚假的停车监督。

## Scene 级划分

训练集和验证集按 scene 划分，而不是随机打散关键帧。这样可以防止同一连续
驾驶片段的相邻图像同时出现在训练集和验证集，降低数据泄漏。

当前真实构建结果见
[`data/nuscenes_vla_sft/dataset_report.md`](../data/nuscenes_vla_sft/dataset_report.md)：

- 有效样本 344 条；
- 训练集 310 条，共 9 个 scene；
- 验证集 34 条，共 1 个 scene；
- 两个集合的 scene 无交集。

由于 mini 版一共只有 10 个 scene，9:1 划分得到的单个验证 scene 不包含
STOP、TURN_RIGHT 和 LOW risk。保留 scene 隔离比随机打散相邻帧更重要，但
最终分类指标必须结合这个类别覆盖限制解读。

trainval v1 构建结果：

- 有效样本 23349 条；
- 训练集 21030 条；
- 验证集 2319 条；
- action 分布：KEEP_LANE 13598、TURN_LEFT 2091、TURN_RIGHT 2764、
  SLOW_DOWN 778、STOP 4118。

trainval v2 构建结果见
[`data/nuscenes_vla_sft_trainval_v2/dataset_report.md`](../data/nuscenes_vla_sft_trainval_v2/dataset_report.md)：

- 有效样本仍为 23349 条；
- 使用 `--action-rule v2` 重新生成动作弱标签；
- 原始训练集 21030 条，均衡采样后训练集 19135 条；
- 均衡后训练集每类 action 都是 3827 条；
- 验证集保持真实 scene 分布，不做均衡采样。

v2 的目标不是“让指标变好看”，而是让训练时模型更频繁地看到低频动作，
尤其是 `SLOW_DOWN`，同时保留真实验证集用于判断改动是否有效。

trainval v3 构建结果见
[`data/nuscenes_vla_sft_trainval_v3_nobalance/dataset_report.md`](../data/nuscenes_vla_sft_trainval_v3_nobalance/dataset_report.md)：

- 继续使用 `--action-rule v2`；
- 不做训练集重采样，用来单独观察动作弱标签规则的影响；
- 训练样本 21030 条，验证样本 2319 条；
- 训练集 action 分布：KEEP_LANE 9915、TURN_LEFT 1604、TURN_RIGHT 2194、
  SLOW_DOWN 3490、STOP 3827。

trainval v4 构建结果见
[`data/nuscenes_vla_sft_trainval_v4_mildsample/dataset_report.md`](../data/nuscenes_vla_sft_trainval_v4_mildsample/dataset_report.md)：

- 继续使用 `--action-rule v2`；
- 不强行拉平成每类一样多，而是对少数类做温和目标采样；
- 训练样本 26742 条，验证样本 2319 条；
- 训练集 action 分布：KEEP_LANE 9915、TURN_LEFT 3000、TURN_RIGHT 3000、
  SLOW_DOWN 7000、STOP 3827；
- 验证集仍保持 scene split 后的真实分布，不做重采样。

v4 的目的不是替代 v1 的完整结论，而是做一个短对照实验：看增加 `SLOW_DOWN`
和转向样本后，模型是否仍然只偏向直线轨迹。

trainval v5 构建结果见
[`data/nuscenes_vla_sft_trainval_v5_history/dataset_report.md`](../data/nuscenes_vla_sft_trainval_v5_history/dataset_report.md)：

- 使用 `--history-steps 3`，每条样本额外读取当前帧之前 3 个关键帧；
- 使用 `--action-rule v3`，让 `SLOW_DOWN` 更依赖速度下降趋势，而不是只靠采样；
- 不做训练集重采样，先验证历史 ego motion 是否真的提供有效信息；
- 有效样本 21297 条，训练样本 19182 条，验证样本 2115 条；
- 训练集 action 分布：KEEP_LANE 7991、TURN_LEFT 1447、TURN_RIGHT 1987、
  SLOW_DOWN 4264、STOP 3493；
- scene 开头历史不足的样本跳过 2550 条。

v5 prompt 中的历史运动字段只来自当前帧之前的 ego pose，不使用未来轨迹，
因此不是答案泄漏。它提供的是类似“速度表”和“过去航向变化”的信息，用来帮助模型
区分 KEEP_LANE、SLOW_DOWN、STOP 和弯道持续转向。

## 重新构建

```bash
env -u PYTHONPATH \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
scripts/convert_nuscenes_to_qwen3vl.py \
  --nuscenes_root /home/pc/datasets/nuscenes \
  --output_dir data/nuscenes_vla_sft \
  --train_ratio 0.9 \
  --future_steps 6 \
  --camera CAM_FRONT
```

构建 trainval v2：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/convert_nuscenes_to_qwen3vl.py \
  --nuscenes-root /home/pc/datasets/Full_dataest \
  --version v1.0-trainval \
  --output-dir data/nuscenes_vla_sft_trainval_v2 \
  --train-ratio 0.9 \
  --future-steps 6 \
  --camera CAM_FRONT \
  --action-rule v2 \
  --balance-train
```

构建 trainval v4：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/convert_nuscenes_to_qwen3vl.py \
  --nuscenes-root /home/pc/datasets/Full_dataest \
  --version v1.0-trainval \
  --output-dir data/nuscenes_vla_sft_trainval_v4_mildsample \
  --train-ratio 0.9 \
  --future-steps 6 \
  --camera CAM_FRONT \
  --action-rule v2 \
  --action-target-counts-json '{"SLOW_DOWN": 7000, "TURN_LEFT": 3000, "TURN_RIGHT": 3000}'
```

构建 trainval v5：

```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 \
  /home/pc/miniconda3/envs/drivevla_sft/bin/python \
  scripts/convert_nuscenes_to_qwen3vl.py \
  --nuscenes-root /home/pc/datasets/Full_dataest \
  --version v1.0-trainval \
  --output-dir data/nuscenes_vla_sft_trainval_v5_history \
  --train-ratio 0.9 \
  --future-steps 6 \
  --history-steps 3 \
  --camera CAM_FRONT \
  --action-rule v3
```

转换脚本同时生成：

- `train.jsonl` / `val.jsonl`：自写训练与评估脚本使用；
- `drivevla_train.json` / `drivevla_val.json`：LLaMA-Factory 使用；
- `summary.json`：机器可读的数据统计；
- `dataset_report.md`：人工检查报告。
