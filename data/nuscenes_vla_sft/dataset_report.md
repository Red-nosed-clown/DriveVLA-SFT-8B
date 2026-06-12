# nuScenes-mini VLA 数据报告

## 数据概览

- 成功转换：344
- 训练样本：310
- 验证样本：34
- 训练场景：9
- 验证场景：1
- 轨迹点数：6
- 平均未来轨迹路程：16.78 米
- 缺失图片：0
- scene 末尾未来帧不足：60
- 缺失相机关键帧：0

## Action 分布

- KEEP_LANE: 188
- TURN_LEFT: 36
- TURN_RIGHT: 28
- SLOW_DOWN: 4
- STOP: 88

## Risk 分布

- LOW: 60
- MEDIUM: 94
- HIGH: 190

## 标签说明

- 轨迹由未来 ego pose 转换到当前自车坐标系得到。
- Risk 是根据交通参与者数量生成的 heuristic 弱监督标签，不是真实人工风险标注。
- 数据按 scene 切分，训练场景与验证场景没有交集。
