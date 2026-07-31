# nuScenes VLA 数据报告

## 数据概览

- 成功转换：21297
- 训练样本：19182
- 验证样本：2115
- 训练场景：616
- 验证场景：68
- 轨迹点数：6
- 动作标签规则：v3
- 历史自车运动步数：3
- 训练集动作均衡采样：False
- 平均未来轨迹路程：15.01 米
- scene 开头历史帧不足：2550
- 缺失图片：5202
- scene 末尾未来帧不足：5100
- 缺失相机关键帧：0

## Action 分布

- KEEP_LANE: 8873
- TURN_LEFT: 1676
- TURN_RIGHT: 2202
- SLOW_DOWN: 4713
- STOP: 3833

## 训练集 Action 分布

- KEEP_LANE: 7991
- TURN_LEFT: 1447
- TURN_RIGHT: 1987
- SLOW_DOWN: 4264
- STOP: 3493

## 验证集 Action 分布

- KEEP_LANE: 882
- TURN_LEFT: 229
- TURN_RIGHT: 215
- SLOW_DOWN: 449
- STOP: 340

## Risk 分布

- LOW: 4365
- MEDIUM: 8789
- HIGH: 8143

## 标签说明

- 轨迹由未来 ego pose 转换到当前自车坐标系得到。
- 历史自车运动只使用当前帧之前的 ego pose，不包含未来答案。
- Risk 是根据交通参与者数量生成的 heuristic 弱监督标签，不是真实人工风险标注。
- Action 也是由未来 ego pose 生成的 heuristic 弱监督标签，不是真实人工驾驶意图标注。
- 数据按 scene 切分，训练场景与验证场景没有交集。
