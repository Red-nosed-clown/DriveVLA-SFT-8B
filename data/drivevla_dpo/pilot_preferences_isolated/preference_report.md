# DriveVLA DPO 偏好数据报告

- 输入预测：512
- 可用偏好对：372
- 训练 / 验证：336 / 36
- 训练 / 验证 scene：247 / 28
- scene 交集：0
- 图片全部存在：True
- 平均偏好间隔：0.3509

## 失败类别

| Category | Count |
|---|---:|
| other_action_error | 19 |
| slow_keep_confusion | 66 |
| stop_confusion | 14 |
| trajectory_error | 120 |
| turn_action_error | 36 |
| turn_geometry | 117 |

## 隔离字段

| Field | Count |
|---|---:|
| action | 135 |
| trajectory | 237 |

## 动作混淆

| Ground Truth -> Prediction | Count |
|---|---:|
| KEEP_LANE->SLOW_DOWN | 2 |
| KEEP_LANE->TURN_LEFT | 4 |
| SLOW_DOWN->KEEP_LANE | 64 |
| SLOW_DOWN->STOP | 11 |
| SLOW_DOWN->TURN_LEFT | 8 |
| SLOW_DOWN->TURN_RIGHT | 7 |
| STOP->SLOW_DOWN | 1 |
| TURN_LEFT->KEEP_LANE | 14 |
| TURN_LEFT->SLOW_DOWN | 2 |
| TURN_LEFT->STOP | 1 |
| TURN_LEFT->TURN_RIGHT | 1 |
| TURN_RIGHT->KEEP_LANE | 14 |
| TURN_RIGHT->SLOW_DOWN | 1 |
| TURN_RIGHT->STOP | 1 |
| TURN_RIGHT->TURN_LEFT | 4 |
