# 数据构建

## 数据来源

第一版只使用本机 `nuScenes-mini`：

```text
/home/pc/datasets/nuscenes
```

输入模态为 `CAM_FRONT` 前视图像，监督信号来自 nuScenes 的 ego pose 和
目标标注。Risk 是根据车辆、行人和障碍物数量生成的 heuristic 弱监督，
不是人工风险真值。

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

转换脚本同时生成：

- `train.jsonl` / `val.jsonl`：自写训练与评估脚本使用；
- `drivevla_train.json` / `drivevla_val.json`：LLaMA-Factory 使用；
- `summary.json`：机器可读的数据统计；
- `dataset_report.md`：人工检查报告。
