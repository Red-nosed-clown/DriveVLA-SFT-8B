# DriveVLA 失败案例分析

- 失败样本总数：25
- 展示样本数：20

## 1. 95c0a92d52584756832ec795d346e296

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800854412460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：7.307211042469149
- FDE：14.01588384655067
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      1.59,
      0.16
    ],
    [
      3.39,
      0.8
    ],
    [
      5.3,
      1.99
    ],
    [
      7.32,
      3.6
    ],
    [
      9.46,
      5.47
    ],
    [
      11.77,
      7.61
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 2. f65ffdc408fb4a0c8ef0d1614b47dce8

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800853412460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：5.37238632101465
- FDE：10.336174340634933
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      1.26,
      0.09
    ],
    [
      2.55,
      0.42
    ],
    [
      3.98,
      1.13
    ],
    [
      5.44,
      2.36
    ],
    [
      6.82,
      4.15
    ],
    [
      8.14,
      6.37
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 3. d1136fce62f14400a069613e274f46f7

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800852912460.jpg`
- 错误类型：Action error, Large FDE
- ADE：4.900886812465304
- FDE：9.0931622662306
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      1.32,
      0.05
    ],
    [
      2.56,
      0.28
    ],
    [
      3.81,
      0.74
    ],
    [
      5.16,
      1.6
    ],
    [
      6.48,
      2.98
    ],
    [
      7.66,
      4.9
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 4. 8178cfbc864e4cb0b6e35746b32bed9f

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800851412460.jpg`
- 错误类型：Action error
- ADE：4.6979376015525105
- FDE：7.920858539325141
- 可能原因：当前帧视觉和统计信息不足以区分相近动作，也可能受到动作类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      1.36,
      -0.01
    ],
    [
      2.75,
      -0.01
    ],
    [
      4.1,
      0.02
    ],
    [
      5.41,
      0.15
    ],
    [
      6.63,
      0.44
    ],
    [
      7.86,
      0.98
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 5. a43568a562a043f38af0ec0b71520af7

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800852412460.jpg`
- 错误类型：Action error, Large FDE
- ADE：4.696956020803384
- FDE：8.362924129752702
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      1.35,
      0.02
    ],
    [
      2.66,
      0.14
    ],
    [
      3.89,
      0.42
    ],
    [
      5.12,
      0.94
    ],
    [
      6.42,
      1.87
    ],
    [
      7.68,
      3.31
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 6. 07c29094cb6144aa889c16c52f762d79

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800851912460.jpg`
- 错误类型：Action error, Large FDE
- ADE：4.678430671573897
- FDE：8.023122833410941
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      1.39,
      -0.0
    ],
    [
      2.74,
      0.03
    ],
    [
      4.05,
      0.16
    ],
    [
      5.27,
      0.45
    ],
    [
      6.5,
      0.99
    ],
    [
      7.79,
      1.92
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 7. 3b594831ff7f4e27a9889c7b7d0d8e92

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800850912460.jpg`
- 错误类型：Action error
- ADE：4.667092225816256
- FDE：7.9311285451693445
- 可能原因：当前帧视觉和统计信息不足以区分相近动作，也可能受到动作类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      1.29,
      -0.01
    ],
    [
      2.65,
      -0.02
    ],
    [
      4.04,
      -0.02
    ],
    [
      5.39,
      0.0
    ],
    [
      6.7,
      0.13
    ],
    [
      7.92,
      0.42
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 8. fb61d590dd1143ccb12ea56fbe9d9d07

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800850412460.jpg`
- 错误类型：Action error
- ADE：4.348542218137017
- FDE：7.700415573201228
- 可能原因：当前帧视觉和统计信息不足以区分相近动作，也可能受到动作类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      1.01,
      -0.01
    ],
    [
      2.29,
      -0.02
    ],
    [
      3.66,
      -0.04
    ],
    [
      5.04,
      -0.06
    ],
    [
      6.39,
      -0.04
    ],
    [
      7.7,
      0.08
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 9. 49dfd2f2fef447cc9b8dec3e17c1c919

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800861912460.jpg`
- 错误类型：Risk error
- ADE：4.018652617687608
- FDE：7.854304552282144
- 可能原因：Risk 是数量规则生成的弱标签，模型可能没有学到规则阈值或受到类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.79,
      -0.01
    ],
    [
      9.81,
      -0.05
    ],
    [
      15.08,
      -0.09
    ],
    [
      20.49,
      -0.16
    ],
    [
      26.08,
      -0.22
    ],
    [
      31.85,
      -0.27
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.0,
      -0.01
    ],
    [
      8.0,
      -0.01
    ],
    [
      12.0,
      -0.01
    ],
    [
      16.0,
      -0.01
    ],
    [
      20.0,
      -0.01
    ],
    [
      24.0,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.0, -0.01], [8.0, -0.01], [12.0, -0.01], [16.0, -0.01], [20.0, -0.01], [24.0, -0.01]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 10. 07175443e8444b8c8c4802fd004e33c1

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800855912460.jpg`
- 错误类型：Action error
- ADE：3.8743556490479416
- FDE：5.755345341506451
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      2.58,
      0.05
    ],
    [
      5.42,
      0.24
    ],
    [
      8.55,
      0.54
    ],
    [
      11.41,
      0.85
    ],
    [
      14.85,
      1.3
    ],
    [
      18.54,
      1.81
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.0,
      -0.01
    ],
    [
      8.0,
      -0.01
    ],
    [
      12.0,
      -0.01
    ],
    [
      16.0,
      -0.01
    ],
    [
      20.0,
      -0.01
    ],
    [
      24.0,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.0, -0.01], [8.0, -0.01], [12.0, -0.01], [16.0, -0.01], [20.0, -0.01], [24.0, -0.01]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 11. 1e0d1b76ea134c7db0592c4510f5e737

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800849912460.jpg`
- 错误类型：Action error
- ADE：3.8119126872720366
- FDE：7.140252096389874
- 可能原因：当前帧视觉和统计信息不足以区分相近动作，也可能受到动作类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      0.75,
      -0.0
    ],
    [
      1.75,
      -0.02
    ],
    [
      3.04,
      -0.03
    ],
    [
      4.4,
      -0.06
    ],
    [
      5.79,
      -0.08
    ],
    [
      7.14,
      -0.06
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 12. 0915646e387b484785ae2b847ffdee2f

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800853912460.jpg`
- 错误类型：Action error, Large FDE
- ADE：3.5866768603548835
- FDE：8.226402615967686
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      1.33,
      0.12
    ],
    [
      2.86,
      0.6
    ],
    [
      4.49,
      1.58
    ],
    [
      6.13,
      3.13
    ],
    [
      7.79,
      5.11
    ],
    [
      9.51,
      7.38
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      1.0,
      -0.01
    ],
    [
      2.0,
      -0.02
    ],
    [
      3.0,
      -0.03
    ],
    [
      4.0,
      -0.04
    ],
    [
      5.0,
      -0.05
    ],
    [
      6.0,
      -0.06
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[1.0, -0.01], [2.0, -0.02], [3.0, -0.03], [4.0, -0.04], [5.0, -0.05], [6.0, -0.06]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 13. 98fa81992fb04e799c329eca220e7164

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800861412460.jpg`
- 错误类型：Risk error
- ADE：3.4278988379208855
- FDE：6.803241874283172
- 可能原因：Risk 是数量规则生成的弱标签，模型可能没有学到规则阈值或受到类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.72,
      -0.01
    ],
    [
      9.51,
      -0.03
    ],
    [
      14.53,
      -0.06
    ],
    [
      19.79,
      -0.1
    ],
    [
      25.21,
      -0.17
    ],
    [
      30.8,
      -0.22
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.0,
      -0.01
    ],
    [
      8.0,
      -0.01
    ],
    [
      12.0,
      -0.01
    ],
    [
      16.0,
      -0.01
    ],
    [
      20.0,
      -0.01
    ],
    [
      24.0,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.0, -0.01], [8.0, -0.01], [12.0, -0.01], [16.0, -0.01], [20.0, -0.01], [24.0, -0.01]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 14. 9c7c7d5d109c40fcaecd3c422d37b4f6

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800854912460.jpg`
- 错误类型：Action error
- ADE：3.092754648280331
- FDE：6.707197626430878
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      1.9,
      0.2
    ],
    [
      4.04,
      0.9
    ],
    [
      6.38,
      1.99
    ],
    [
      8.9,
      3.31
    ],
    [
      11.64,
      4.85
    ],
    [
      14.13,
      6.3
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      2.0,
      -0.01
    ],
    [
      4.0,
      -0.02
    ],
    [
      5.99,
      -0.03
    ],
    [
      7.99,
      -0.04
    ],
    [
      10.0,
      -0.05
    ],
    [
      12.0,
      -0.06
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[2.0, -0.01], [4.0, -0.02], [5.99, -0.03], [7.99, -0.04], [10.0, -0.05], [12.0, -0.06]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 15. 648fe1aeca944fb793b334cb6ee01854

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800849412460.jpg`
- 错误类型：Action error
- ADE：3.06691255012073
- FDE：6.23065004634348
- 可能原因：当前帧视觉和统计信息不足以区分相近动作，也可能受到动作类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      0.44,
      0.0
    ],
    [
      1.19,
      -0.0
    ],
    [
      2.2,
      -0.02
    ],
    [
      3.49,
      -0.04
    ],
    [
      4.85,
      -0.07
    ],
    [
      6.23,
      -0.09
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 16. 056becbc0d5a46da8d59eebddedb47bb

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800856412460.jpg`
- 错误类型：Action error
- ADE：2.97788978843875
- FDE：3.7789548819746446
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      2.85,
      0.02
    ],
    [
      5.99,
      0.13
    ],
    [
      8.86,
      0.28
    ],
    [
      12.32,
      0.52
    ],
    [
      16.03,
      0.8
    ],
    [
      20.41,
      1.17
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.0,
      -0.01
    ],
    [
      8.0,
      -0.01
    ],
    [
      12.0,
      -0.01
    ],
    [
      16.0,
      -0.01
    ],
    [
      20.0,
      -0.01
    ],
    [
      24.0,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.0, -0.01], [8.0, -0.01], [12.0, -0.01], [16.0, -0.01], [20.0, -0.01], [24.0, -0.01]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 17. 7d82aa0c679141d1a71733b85fdcd3ed

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800855412460.jpg`
- 错误类型：Action error
- ADE：2.459374929172763
- FDE：4.370286031829036
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      2.25,
      0.18
    ],
    [
      4.78,
      0.7
    ],
    [
      7.54,
      1.4
    ],
    [
      10.56,
      2.25
    ],
    [
      13.32,
      3.08
    ],
    [
      16.62,
      4.14
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      3.0,
      -0.01
    ],
    [
      5.99,
      -0.01
    ],
    [
      8.99,
      -0.01
    ],
    [
      11.99,
      -0.01
    ],
    [
      14.99,
      -0.01
    ],
    [
      17.99,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[3.0, -0.01], [5.99, -0.01], [8.99, -0.01], [11.99, -0.01], [14.99, -0.01], [17.99, -0.01]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 18. 8d7dcd1533704f5882a5afcb65509ed5

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800860412460.jpg`
- 错误类型：Risk error
- ADE：2.4284166172512816
- FDE：4.900459162160216
- 可能原因：Risk 是数量规则生成的弱标签，模型可能没有学到规则阈值或受到类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.49,
      -0.03
    ],
    [
      9.1,
      -0.08
    ],
    [
      13.82,
      -0.13
    ],
    [
      18.61,
      -0.18
    ],
    [
      23.63,
      -0.25
    ],
    [
      28.89,
      -0.33
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.0,
      -0.01
    ],
    [
      8.0,
      -0.01
    ],
    [
      12.0,
      -0.01
    ],
    [
      16.0,
      -0.01
    ],
    [
      20.0,
      -0.01
    ],
    [
      24.0,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.0, -0.01], [8.0, -0.01], [12.0, -0.01], [16.0, -0.01], [20.0, -0.01], [24.0, -0.01]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 19. 77fc24547ab34182a945eecb825b6576

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800848912460.jpg`
- 错误类型：Action error
- ADE：2.2251996670532503
- FDE：5.040634880647477
- 可能原因：当前帧视觉和统计信息不足以区分相近动作，也可能受到动作类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      0.2,
      -0.0
    ],
    [
      0.64,
      -0.0
    ],
    [
      1.39,
      -0.01
    ],
    [
      2.4,
      -0.03
    ],
    [
      3.68,
      -0.05
    ],
    [
      5.04,
      -0.08
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "STOP",
  "risk": "HIGH",
  "trajectory": [
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ],
    [
      -0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "STOP", "risk": "HIGH", "trajectory": [[-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0], [-0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 20. c18d3bcc9297454ba52112c079cb756e

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800862412460.jpg`
- 错误类型：Risk error
- ADE：1.9781957352756703
- FDE：4.367161549565121
- 可能原因：Risk 是数量规则生成的弱标签，模型可能没有学到规则阈值或受到类别不均衡影响。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      5.02,
      -0.03
    ],
    [
      10.29,
      -0.06
    ],
    [
      15.7,
      -0.13
    ],
    [
      21.29,
      -0.18
    ],
    [
      27.06,
      -0.22
    ],
    [
      33.06,
      -0.26
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.81,
      -0.01
    ],
    [
      9.6,
      -0.01
    ],
    [
      14.38,
      -0.01
    ],
    [
      19.16,
      -0.01
    ],
    [
      23.93,
      -0.01
    ],
    [
      28.7,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.81, -0.01], [9.6, -0.01], [14.38, -0.01], [19.16, -0.01], [23.93, -0.01], [28.7, -0.01]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```
