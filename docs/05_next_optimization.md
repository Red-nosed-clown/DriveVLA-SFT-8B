# 下一步优化计划

本文档记录 trainval 完整训练后的下一轮优化方向。当前不要急着单纯增加 epoch，
因为问题已经从“不会按格式输出”和“只会预测直行”变成了更细的轨迹形状和少数动作类别问题。

## 当前结论

Trainval QLoRA 已经完成 3 epoch，并在 2319 条验证样本上完成评估：

- Parse Success：99.83%；
- Action Accuracy：80.42%；
- Risk Accuracy：95.34%；
- Trajectory Valid：99.83%；
- ADE：2.2574 m；
- FDE：3.9219 m。

动作类别塌缩已经明显缓解，但还存在三个核心问题：

- `SLOW_DOWN` 最弱，63 条验证样本中只预测正确 8 条；
- `STOP` 仍有一部分被预测成 `KEEP_LANE`；
- 预测轨迹比真实轨迹更直，GT 平均弯曲度 0.2023，预测平均弯曲度 0.1085。

## 优化优先级

### 1. 先改评估，不急着重训

继续保留 ADE/FDE，但每次实验都同时记录：

- 每类 action accuracy；
- action confusion matrix；
- trajectory curvature；
- final lateral error；
- `SLOW_DOWN` 和 `STOP` 的失败样本列表。

原因是 ADE/FDE 只能说明点位误差，不能完整说明轨迹是否过度平滑。现在肉眼看到
“轨迹都是直线”，正是 ADE/FDE 不够敏感的地方。

### 2. 优化 SLOW_DOWN / STOP 标签规则

当前动作标签主要来自未来 6 个关键帧轨迹的几何启发式规则，例如终点前向距离、终点
横向位移和平均转向趋势。下一版转换脚本建议增加：

- 未来 6 点累计路径长度；
- 平均速度；
- 最后一段速度；
- 速度下降趋势；
- 近似静止但未完全停车的中间状态。

这样可以把真正的 `SLOW_DOWN` 和普通 `KEEP_LANE` 区分得更清楚，也能减少 STOP /
KEEP_LANE 的边界混淆。

### 3. 做动作均衡采样

训练集里 KEEP_LANE 占比最高，SLOW_DOWN 最少。下一版可以生成一个平衡训练文件：

- 保留全部 `SLOW_DOWN`；
- 对 `SLOW_DOWN` 做过采样；
- 对 `STOP` 做轻度过采样；
- 对 `KEEP_LANE` 做上限采样；
- 验证集仍然按 scene 划分，不做重采样。

注意：重采样只用于训练集，验证集必须保持真实分布，否则指标会失真。

### 4. 加入历史运动状态

只看当前 `CAM_FRONT` 图片时，模型很难判断自车是在加速、减速还是即将停车。下一版数据
可以在 prompt 中加入结构化历史信息：

- 当前速度估计；
- 过去 1 秒位移；
- 过去 1 秒 yaw 变化；
- 最近速度变化趋势。

如果显存允许，再尝试多图输入，例如当前帧加上一帧历史图像。第一版先加文本数值特征，
因为它对训练链路改动最小。

### 5. 改善弯道轨迹形状

当前模型已经能预测 TURN_LEFT / TURN_RIGHT，但横向位移和弯曲度偏保守。可以尝试：

- 在数据报告里统计每类动作的曲率分布；
- 在 assistant JSON 中额外加入 `motion_pattern` 或 `curvature_hint` 教学字段；
- 在 prompt 中明确要求轨迹点反映道路曲率；
- 后续加入 `CAM_FRONT_LEFT` 和 `CAM_FRONT_RIGHT`；
- 更进一步再考虑地图 lane centerline。

第一阶段不建议同时引入所有信息。先用曲率指标判断每次改动是否真的让轨迹更像真实轨迹。

## 建议实验顺序

1. 生成 v2 数据报告，只改标签统计和数据报告，先不训练；已完成。
2. 确认 `SLOW_DOWN` / `STOP` 分布更合理；已完成。
3. 注册 `drivevla_trainval_v2_train` 和 `drivevla_trainval_v2_val`；已完成。
4. 先跑 32 条冒烟训练；已完成。
5. 跑 v2 1000 step 对照实验；已完成，强均衡采样效果不理想。
6. 跑 v3 1000 step 对照实验；已完成，动作准确率恢复，但轨迹更偏直。
7. 生成 v4 温和采样数据并通过 2 step 冒烟训练；已完成。
8. 跑 v4 1000 step 短训练；已完成，温和采样改善了部分几何指标，但动作分类退化。
9. 比较 v1 / v2 / v3 / v4 的 action accuracy、SLOW_DOWN accuracy、ADE/FDE 和曲率；已完成。
10. 生成 v5 历史运动数据并通过 2 step 冒烟训练；已完成。
11. 跑 v5 1000 step 短训练；下一步。

## v2 已完成记录

v2 数据已经生成到 `data/nuscenes_vla_sft_trainval_v2`，核心变化如下：

- 动作规则：`v2`；
- 总样本：23349；
- 原始训练样本：21030；
- 均衡后训练样本：19135；
- 验证样本：2319；
- 训练集每类 action：3827；
- 验证集 `SLOW_DOWN`：360，明显多于 v1 的 63。

v2 冒烟训练已经通过，输出目录为
`results/qwen3vl_8b_drivevla_trainval_v2_smoke`。这证明 v2 数据、注册名、图片路径、
Qwen3-VL processor、4bit QLoRA 和 adapter 保存链路都是通的。

v2 1000 step 短训练已经完成，但结果不理想：Action Acc 55.50%，ADE 2.8402 m，
FDE 4.9668 m，预测近似直线比例 55.00%。同样前 200 条上，v1 完整模型按 v2
标签重评仍有 72.00% Action Acc，且预测近似直线比例只有 24.00%。这说明 v2 的
强均衡采样很可能破坏了训练分布。

## v3 当前实验

v3 保留 `--action-rule v2`，但去掉 `--balance-train`。这样只验证“新的动作弱标签”
本身，不再混入强均衡采样的影响。

v3 数据已经生成到 `data/nuscenes_vla_sft_trainval_v3_nobalance`：

- 总样本：23349；
- 训练样本：21030；
- 验证样本：2319；
- 训练集 action 分布：KEEP_LANE 9915、TURN_LEFT 1604、TURN_RIGHT 2194、
  SLOW_DOWN 3490、STOP 3827；
- 验证集 action 分布：KEEP_LANE 1107、TURN_LEFT 242、TURN_RIGHT 235、
  SLOW_DOWN 360、STOP 375。

v3 冒烟训练已经通过，输出目录为
`results/qwen3vl_8b_drivevla_trainval_v3_nobalance_smoke`。

v3 1000 step 短训练已经完成：Action Acc 70.50%，ADE 2.3278 m，FDE 4.0743 m。
它比 v2 强均衡采样更稳，但轨迹几何继续退化，前 200 条验证样本中预测近似直线
比例达到 73.50%，并且没有预测出 `SLOW_DOWN`。这说明单纯取消均衡可以恢复动作
主分布，但不能解决速度类动作和轨迹形状问题。

## v4 当前实验

v4 继续保留 `--action-rule v2`，但把强均衡改成温和目标采样。它的思路是：
`KEEP_LANE` 和 `STOP` 保持原始训练数量，只增加训练中过少或难学的动作，
避免 v2 那样把所有 action 都拉成完全相同数量。

v4 数据已经生成到 `data/nuscenes_vla_sft_trainval_v4_mildsample`：

- 总样本：23349；
- 采样后训练样本：26742；
- 验证样本：2319；
- 训练集 action 分布：KEEP_LANE 9915、TURN_LEFT 3000、TURN_RIGHT 3000、
  SLOW_DOWN 7000、STOP 3827；
- 验证集 action 分布：KEEP_LANE 1107、TURN_LEFT 242、TURN_RIGHT 235、
  SLOW_DOWN 360、STOP 375。

v4 冒烟训练已经通过，输出目录为
`results/qwen3vl_8b_drivevla_trainval_v4_mildsample_smoke`。

v4 1000 step 短训练已经完成：

- Action Acc：62.00%；
- Risk Acc：95.00%；
- ADE：2.2551 m；
- FDE：3.9832 m；
- 预测平均弯曲度：0.0684；
- 预测近似直线比例：64.50%；
- 预测动作分布：KEEP_LANE 124、SLOW_DOWN 23、TURN_LEFT 32、TURN_RIGHT 21。

和 v3 相比，v4 的 ADE/FDE 略好，预测近似直线比例从 73.50% 降到 64.50%，
说明温和采样确实让轨迹几何稍微“活”了一点。但 Action Acc 从 70.50% 降到
62.00%，`SLOW_DOWN` 只预测正确 2/17，并把 20 条 KEEP_LANE 误判成
SLOW_DOWN。这说明只靠采样增加 `SLOW_DOWN` 样本，会让模型更敢输出
`SLOW_DOWN`，但还没有学到真正的减速判据。

短训练后的判断结果：

- `SLOW_DOWN` 开始被预测，但正确率没有实质提高；
- ADE/FDE 不劣于 v3；
- 预测近似直线比例低于 v3，但仍远高于 v1 完整模型的 33.00%；
- 温和采样不是当前最优解，下一步应该给 prompt 加历史运动状态。

## v5 当前实验

只看当前 `CAM_FRONT` 图像和目标统计，模型很难区分“继续保持车道”和“正在减速”。
v5 因此在 prompt 中加入最近历史 ego motion：

- `history_speed_mps`：过去若干关键帧估计速度；
- `current_speed_mps`：当前附近速度估计；
- `history_accel_mps2`：过去速度变化趋势；
- `history_yaw_delta_deg`：过去一小段时间的航向变化；
- `history_lateral_delta_m`：过去横向位移趋势。

这样 `SLOW_DOWN` 不再只依赖未来轨迹弱标签和图像外观，而是能在输入里看到速度正在下降。
v5 第一版仍然只用单目 `CAM_FRONT`，不同时引入多相机，避免变量太多。

v5 数据已经生成到 `data/nuscenes_vla_sft_trainval_v5_history`：

- 动作规则：`v3`；
- 历史步数：3；
- 总样本：21297；
- 训练样本：19182；
- 验证样本：2115；
- 训练集 action 分布：KEEP_LANE 7991、TURN_LEFT 1447、TURN_RIGHT 1987、
  SLOW_DOWN 4264、STOP 3493；
- 验证集 action 分布：KEEP_LANE 882、TURN_LEFT 229、TURN_RIGHT 215、
  SLOW_DOWN 449、STOP 340。

v5 冒烟训练已经通过，输出目录为
`results/qwen3vl_8b_drivevla_trainval_v5_history_smoke`，2 step train loss
为 1.3777。

v5 1000 step 短训练已经完成，eval loss 为 0.3138，明显低于 v2/v3/v4 短训练
的约 0.338。前 200 条验证样本的自写评估结果：

- Action Acc：59.00%；
- Risk Acc：93.00%；
- ADE：0.9097 m；
- FDE：2.0478 m；
- 预测平均弯曲度：0.0757；
- 预测近似直线比例：47.50%；
- 预测动作分布：KEEP_LANE 126、SLOW_DOWN 14、TURN_LEFT 51、TURN_RIGHT 9。

和 v4 相比，v5 的 ADE/FDE 大幅下降，预测近似直线比例从 64.50% 降到
47.50%，说明历史 ego motion 对连续轨迹拟合非常有效。但 Action Acc 没有提升，
主要问题是 `SLOW_DOWN` 和 `TURN_RIGHT`：

- KEEP_LANE：83/110，75.45%；
- SLOW_DOWN：1/30，3.33%；
- TURN_LEFT：30/46，65.22%；
- TURN_RIGHT：4/14，28.57%。

额外用预测轨迹反推 action 后，轨迹派生 action 的准确率为 58.00%，和模型输出的
action 字段 59.00% 接近。这说明 v5 不是“文字 action 写错但轨迹对了”，而是
轨迹虽然数值误差很低，但在弱标签规则下仍偏向 KEEP_LANE。下一步应把 action
监督从单个枚举标签拆得更细，例如增加速度意图字段或显式动作判据，而不是只继续调采样。

原定短训练判断标准：

- Action Acc 至少回到 v3 的 70.50% 附近；
- `SLOW_DOWN` 不再完全不预测，也不要像 v4 那样大量误判 KEEP_LANE；
- ADE/FDE 不劣于 v3 的 2.3278 m / 4.0743 m；
- 预测近似直线比例低于 v4 的 64.50%；
- TURN_LEFT / TURN_RIGHT 的最终横向位移和曲率更接近 GT。

实际判断：

- 轨迹数值和直线化明显改善，v5 是目前最好的轨迹版本；
- `SLOW_DOWN` 没有学好，不能直接把 v5 作为最终动作分类版本；
- 如果时间允许，下一步优先做 v6：保留 v5 历史运动输入，同时在 assistant JSON
  增加 `speed_intent` 或 `motion_state` 字段，把速度变化从 action 枚举里拆出来。

## 简历表达

可以把这部分写成项目亮点：

> 在 QLoRA 微调后，模型动作准确率达到 80.42%，但进一步通过轨迹曲率和横向位移分析发现
> 连续轨迹存在过平滑问题；因此设计了 confusion matrix、curvature metric 和低频动作
> 重采样方案，用于定位并优化 Vision-Language-Action 模型的决策与轨迹生成误差。
