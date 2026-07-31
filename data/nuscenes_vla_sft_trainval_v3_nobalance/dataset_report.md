# nuScenes VLA 数据报告

## 数据概览

- 成功转换：23349
- 训练样本：21030
- 验证样本：2319
- 训练场景：616
- 验证场景：68
- 轨迹点数：6
- 动作标签规则：v2
- 训练集动作均衡采样：False
- 平均未来轨迹路程：14.99 米
- 缺失图片：5700
- scene 末尾未来帧不足：5100
- 缺失相机关键帧：0

## Action 分布

- KEEP_LANE: 11022
- TURN_LEFT: 1846
- TURN_RIGHT: 2429
- SLOW_DOWN: 3850
- STOP: 4202

## 训练集 Action 分布

- KEEP_LANE: 9915
- TURN_LEFT: 1604
- TURN_RIGHT: 2194
- SLOW_DOWN: 3490
- STOP: 3827

## 验证集 Action 分布

- KEEP_LANE: 1107
- TURN_LEFT: 242
- TURN_RIGHT: 235
- SLOW_DOWN: 360
- STOP: 375

## Risk 分布

- LOW: 4939
- MEDIUM: 9717
- HIGH: 8693

## 标签说明

- 轨迹由未来 ego pose 转换到当前自车坐标系得到。
- Risk 是根据交通参与者数量生成的 heuristic 弱监督标签，不是真实人工风险标注。
- Action 也是由未来 ego pose 生成的 heuristic 弱监督标签，不是真实人工驾驶意图标注。
- 数据按 scene 切分，训练场景与验证场景没有交集。
