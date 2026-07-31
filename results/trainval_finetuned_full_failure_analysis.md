# DriveVLA 失败案例分析

- 失败样本总数：702
- 展示样本数：30

## 1. d613b7d559f24f35a4fed9b6e7e75fb5

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-07-24-11-22-45+0800__CAM_FRONT__1532402752112669.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：14.35608542884236
- FDE：24.794015406948507
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      5.52,
      0.01
    ],
    [
      11.71,
      0.17
    ],
    [
      17.37,
      0.44
    ],
    [
      23.08,
      0.81
    ],
    [
      28.8,
      1.24
    ],
    [
      34.44,
      1.69
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "TURN_RIGHT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.7,
      -0.04
    ],
    [
      3.41,
      -0.16
    ],
    [
      5.1,
      -0.38
    ],
    [
      6.78,
      -0.72
    ],
    [
      8.4,
      -1.21
    ],
    [
      9.9,
      -1.85
    ]
  ],
  "reason": "沿道路趋势向右行驶；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "TURN_RIGHT", "risk": "MEDIUM", "trajectory": [[1.7, -0.04], [3.41, -0.16], [5.1, -0.38], [6.78, -0.72], [8.4, -1.21], [9.9, -1.85]], "reason": "沿道路趋势向右行驶；周边存在一定数量的交通参与者。"}
```

## 2. 39b2b27015ed4607969ec08175799ae0

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-07-27-12-07-38-0400__CAM_FRONT__1532707864012404.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：13.045041641432912
- FDE：23.040054253408346
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      3.84,
      -0.02
    ],
    [
      6.92,
      -0.02
    ],
    [
      10.51,
      -0.02
    ],
    [
      14.96,
      -0.04
    ],
    [
      19.0,
      -0.04
    ],
    [
      23.04,
      -0.05
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
      0.0,
      -0.0
    ],
    [
      0.0,
      -0.0
    ],
    [
      0.0,
      -0.0
    ],
    [
      0.0,
      -0.0
    ],
    [
      0.0,
      -0.0
    ],
    [
      0.0,
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
{"action": "STOP", "risk": "HIGH", "trajectory": [[0.0, -0.0], [0.0, -0.0], [0.0, -0.0], [0.0, -0.0], [0.0, -0.0], [0.0, -0.0]], "reason": "停车或低速等待；周边交通参与者密集，需要谨慎决策。"}
```

## 3. 91f3a8d8da9f43e193b6bae4d313d713

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385317662404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：12.530902479108521
- FDE：21.03380374539993
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      1.33,
      0.0
    ],
    [
      2.41,
      0.01
    ],
    [
      3.56,
      0.07
    ],
    [
      4.68,
      0.13
    ],
    [
      5.94,
      0.14
    ],
    [
      7.42,
      0.12
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
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.88,
      -0.01
    ],
    [
      9.7,
      0.02
    ],
    [
      14.46,
      0.09
    ],
    [
      19.18,
      0.21
    ],
    [
      23.85,
      0.36
    ],
    [
      28.45,
      0.52
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
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.88, -0.01], [9.7, 0.02], [14.46, 0.09], [19.18, 0.21], [23.85, 0.36], [28.45, 0.52]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 4. 8a468b35a12b449cbdbfe43bb9b0abd9

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385318162404.jpg`
- 错误类型：Risk error, Large ADE, Large FDE
- ADE：12.41355693654129
- FDE：20.090719250439992
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.09,
      -0.01
    ],
    [
      2.24,
      0.04
    ],
    [
      3.35,
      0.09
    ],
    [
      4.62,
      0.08
    ],
    [
      6.1,
      0.04
    ],
    [
      8.01,
      -0.01
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
      4.88,
      -0.02
    ],
    [
      9.7,
      -0.01
    ],
    [
      14.45,
      0.01
    ],
    [
      19.1,
      0.06
    ],
    [
      23.66,
      0.11
    ],
    [
      28.1,
      0.16
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
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.88, -0.02], [9.7, -0.01], [14.45, 0.01], [19.1, 0.06], [23.66, 0.11], [28.1, 0.16]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 5. f4c7b0dd02d54e02bf5320de75f98fc0

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385317162404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：12.348564113187104
- FDE：20.81105955976293
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.31,
      -0.0
    ],
    [
      2.63,
      0.02
    ],
    [
      3.72,
      0.04
    ],
    [
      4.87,
      0.11
    ],
    [
      5.98,
      0.19
    ],
    [
      7.24,
      0.21
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.88,
      -0.01
    ],
    [
      9.7,
      0.01
    ],
    [
      14.46,
      0.06
    ],
    [
      19.1,
      0.15
    ],
    [
      23.65,
      0.28
    ],
    [
      28.05,
      0.42
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[4.88, -0.01], [9.7, 0.01], [14.46, 0.06], [19.1, 0.15], [23.65, 0.28], [28.05, 0.42]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 6. 3d38fa90aa394a8ba23b52d0b7458d9d

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385316662404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：12.181854861269969
- FDE：21.010687756472894
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.41,
      0.0
    ],
    [
      2.72,
      0.02
    ],
    [
      4.04,
      0.05
    ],
    [
      5.13,
      0.09
    ],
    [
      6.28,
      0.18
    ],
    [
      7.39,
      0.27
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.8,
      -0.01
    ],
    [
      9.6,
      0.01
    ],
    [
      14.38,
      0.06
    ],
    [
      19.1,
      0.15
    ],
    [
      23.78,
      0.28
    ],
    [
      28.4,
      0.44
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[4.8, -0.01], [9.6, 0.01], [14.38, 0.06], [19.1, 0.15], [23.78, 0.28], [28.4, 0.44]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 7. 5624b784c7ec44029e3e284cae9d1cdc

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-07-24-11-22-45+0800__CAM_FRONT__1532402752612460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：12.177292015785532
- FDE：19.810666318930313
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      6.19,
      0.04
    ],
    [
      11.86,
      0.2
    ],
    [
      17.58,
      0.46
    ],
    [
      23.3,
      0.78
    ],
    [
      28.94,
      1.13
    ],
    [
      34.0,
      1.46
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "TURN_RIGHT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      2.21,
      -0.06
    ],
    [
      4.5,
      -0.26
    ],
    [
      6.91,
      -0.66
    ],
    [
      9.46,
      -1.31
    ],
    [
      12.1,
      -2.23
    ],
    [
      14.81,
      -3.46
    ]
  ],
  "reason": "沿道路趋势向右行驶；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "TURN_RIGHT", "risk": "MEDIUM", "trajectory": [[2.21, -0.06], [4.5, -0.26], [6.91, -0.66], [9.46, -1.31], [12.1, -2.23], [14.81, -3.46]], "reason": "沿道路趋势向右行驶；周边存在一定数量的交通参与者。"}
```

## 8. 280d89a549534f0d96c30e263c222448

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385319162404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：11.35992304297842
- FDE：18.084424237448093
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.12,
      -0.02
    ],
    [
      2.38,
      -0.1
    ],
    [
      3.86,
      -0.23
    ],
    [
      5.75,
      -0.4
    ],
    [
      7.85,
      -0.6
    ],
    [
      9.7,
      -0.76
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.85,
      -0.04
    ],
    [
      9.6,
      -0.09
    ],
    [
      14.28,
      -0.14
    ],
    [
      18.9,
      -0.21
    ],
    [
      23.4,
      -0.28
    ],
    [
      27.78,
      -0.36
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[4.85, -0.04], [9.6, -0.09], [14.28, -0.14], [18.9, -0.21], [23.4, -0.28], [27.78, -0.36]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 9. d1194d4a527f4886b178dceae360dff5

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385318662404.jpg`
- 错误类型：Risk error, Large ADE, Large FDE
- ADE：11.218905665925123
- FDE：17.691910580827614
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.15,
      0.01
    ],
    [
      2.27,
      0.03
    ],
    [
      3.53,
      -0.02
    ],
    [
      5.01,
      -0.1
    ],
    [
      6.91,
      -0.22
    ],
    [
      9.02,
      -0.35
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
      4.68,
      -0.03
    ],
    [
      9.3,
      -0.06
    ],
    [
      13.8,
      -0.08
    ],
    [
      18.2,
      -0.09
    ],
    [
      22.51,
      -0.09
    ],
    [
      26.71,
      -0.09
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
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.68, -0.03], [9.3, -0.06], [13.8, -0.08], [18.2, -0.09], [22.51, -0.09], [26.71, -0.09]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 10. 0f9a6335284448e1a6116a5bdd8874dc

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385319662404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：11.063520151006308
- FDE：17.998405484931162
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.26,
      -0.05
    ],
    [
      2.74,
      -0.14
    ],
    [
      4.64,
      -0.27
    ],
    [
      6.75,
      -0.41
    ],
    [
      8.6,
      -0.53
    ],
    [
      10.67,
      -0.63
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.88,
      -0.03
    ],
    [
      9.7,
      -0.06
    ],
    [
      14.5,
      -0.08
    ],
    [
      19.28,
      -0.09
    ],
    [
      24.0,
      -0.09
    ],
    [
      28.66,
      -0.08
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[4.88, -0.03], [9.7, -0.06], [14.5, -0.08], [19.28, -0.09], [24.0, -0.09], [28.66, -0.08]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 11. f332e0493def4d719237a43dbd7c667f

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-07-24-11-13-19+0800__CAM_FRONT__1532402421112460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：10.91053142879518
- FDE：18.326377165168243
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "TURN_RIGHT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.32,
      -0.1
    ],
    [
      8.78,
      -0.35
    ],
    [
      13.79,
      -0.79
    ],
    [
      18.38,
      -1.35
    ],
    [
      23.0,
      -2.04
    ],
    [
      27.56,
      -2.87
    ]
  ],
  "reason": "沿道路趋势向右行驶；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "TURN_LEFT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.2,
      0.02
    ],
    [
      2.6,
      0.11
    ],
    [
      4.18,
      0.3
    ],
    [
      5.91,
      0.61
    ],
    [
      7.79,
      1.06
    ],
    [
      9.81,
      1.69
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "TURN_LEFT", "risk": "MEDIUM", "trajectory": [[1.2, 0.02], [2.6, 0.11], [4.18, 0.3], [5.91, 0.61], [7.79, 1.06], [9.81, 1.69]], "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。"}
```

## 12. f93cc7a0c103455390359660ae258d5f

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385316162404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：10.813017417355526
- FDE：18.528769522016297
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.52,
      0.01
    ],
    [
      2.93,
      0.04
    ],
    [
      4.24,
      0.09
    ],
    [
      5.56,
      0.16
    ],
    [
      6.65,
      0.22
    ],
    [
      7.79,
      0.34
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.58,
      0.01
    ],
    [
      9.1,
      0.09
    ],
    [
      13.52,
      0.22
    ],
    [
      17.88,
      0.41
    ],
    [
      22.16,
      0.64
    ],
    [
      26.31,
      0.91
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[4.58, 0.01], [9.1, 0.09], [13.52, 0.22], [17.88, 0.41], [22.16, 0.64], [26.31, 0.91]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 13. b3160c6dbfa84ddbb25b444472c57124

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-08-02-17-28-51+0800__CAM_FRONT__1533202754662460.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：10.528217785726476
- FDE：18.30354064108909
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      5.77,
      0.02
    ],
    [
      11.44,
      0.06
    ],
    [
      16.89,
      0.13
    ],
    [
      21.79,
      0.19
    ],
    [
      26.97,
      0.26
    ],
    [
      32.1,
      0.35
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      2.8,
      -0.01
    ],
    [
      5.4,
      -0.01
    ],
    [
      7.8,
      -0.01
    ],
    [
      10.0,
      -0.01
    ],
    [
      12.0,
      -0.01
    ],
    [
      13.8,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[2.8, -0.01], [5.4, -0.01], [7.8, -0.01], [10.0, -0.01], [12.0, -0.01], [13.8, -0.01]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 14. 8031e090de524cb99c7a6c5b68d302cf

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385320162404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：10.122678567585497
- FDE：16.085484139434534
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.49,
      -0.03
    ],
    [
      3.39,
      -0.07
    ],
    [
      5.5,
      -0.11
    ],
    [
      7.35,
      -0.15
    ],
    [
      9.43,
      -0.16
    ],
    [
      12.03,
      -0.1
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.88,
      -0.01
    ],
    [
      9.7,
      0.01
    ],
    [
      14.46,
      0.06
    ],
    [
      19.1,
      0.13
    ],
    [
      23.66,
      0.22
    ],
    [
      28.11,
      0.32
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[4.88, -0.01], [9.7, 0.01], [14.46, 0.06], [19.1, 0.13], [23.66, 0.22], [28.11, 0.32]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 15. 2732220f823a4adfb65470a903f23968

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385314662404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：10.088446336539617
- FDE：18.02765930452426
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.88,
      0.05
    ],
    [
      3.59,
      0.21
    ],
    [
      5.13,
      0.45
    ],
    [
      6.62,
      0.74
    ],
    [
      8.01,
      1.03
    ],
    [
      9.28,
      1.32
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "TURN_LEFT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.48,
      0.05
    ],
    [
      8.99,
      0.3
    ],
    [
      13.51,
      0.71
    ],
    [
      18.06,
      1.26
    ],
    [
      22.65,
      1.91
    ],
    [
      27.26,
      2.63
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "TURN_LEFT", "risk": "MEDIUM", "trajectory": [[4.48, 0.05], [8.99, 0.3], [13.51, 0.71], [18.06, 1.26], [22.65, 1.91], [27.26, 2.63]], "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。"}
```

## 16. 1edfa17bad944bf88368ecf37e85fe25

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-08-02-17-28-51+0800__CAM_FRONT__1533202754162460.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：9.833561815879033
- FDE：16.83475274543704
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      5.96,
      -0.0
    ],
    [
      11.72,
      0.04
    ],
    [
      17.39,
      0.12
    ],
    [
      22.85,
      0.21
    ],
    [
      27.74,
      0.29
    ],
    [
      32.93,
      0.39
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      3.1,
      -0.01
    ],
    [
      6.1,
      -0.01
    ],
    [
      8.9,
      -0.01
    ],
    [
      11.5,
      -0.01
    ],
    [
      13.9,
      -0.01
    ],
    [
      16.1,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[3.1, -0.01], [6.1, -0.01], [8.9, -0.01], [11.5, -0.01], [13.9, -0.01], [16.1, -0.01]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 17. 2a6cf3941cfb4e87b687f4129c44ba7a

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-07-24-11-13-19+0800__CAM_FRONT__1532402428662460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：9.68828483861517
- FDE：19.136679440279078
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "TURN_RIGHT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      5.21,
      -0.12
    ],
    [
      10.42,
      -0.42
    ],
    [
      15.17,
      -0.84
    ],
    [
      20.96,
      -1.58
    ],
    [
      26.4,
      -2.5
    ],
    [
      33.15,
      -3.96
    ]
  ],
  "reason": "沿道路趋势向右行驶；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      2.9,
      -0.03
    ],
    [
      5.61,
      -0.09
    ],
    [
      8.1,
      -0.19
    ],
    [
      10.38,
      -0.32
    ],
    [
      12.44,
      -0.48
    ],
    [
      14.3,
      -0.66
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[2.9, -0.03], [5.61, -0.09], [8.1, -0.19], [10.38, -0.32], [12.44, -0.48], [14.3, -0.66]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 18. 66fd74372d564046a3f3eff42f745ef6

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385315162404.jpg`
- 错误类型：Action error, Risk error, Large ADE, Large FDE
- ADE：9.673762158966538
- FDE：17.42047645731884
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      1.71,
      0.05
    ],
    [
      3.27,
      0.18
    ],
    [
      4.77,
      0.37
    ],
    [
      6.17,
      0.57
    ],
    [
      7.46,
      0.77
    ],
    [
      8.77,
      1.0
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
  "action": "TURN_LEFT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.18,
      0.02
    ],
    [
      8.4,
      0.18
    ],
    [
      12.7,
      0.48
    ],
    [
      17.1,
      0.91
    ],
    [
      21.6,
      1.44
    ],
    [
      26.16,
      2.03
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "TURN_LEFT", "risk": "MEDIUM", "trajectory": [[4.18, 0.02], [8.4, 0.18], [12.7, 0.48], [17.1, 0.91], [21.6, 1.44], [26.16, 2.03]], "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。"}
```

## 19. b6032abb0c5f4f5b9cc589d1a3487c67

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-09-18-14-54-39-0400__CAM_FRONT__1537297419412404.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：9.45025959290038
- FDE：15.5104642096876
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "STOP",
  "risk": "MEDIUM",
  "trajectory": [
    [
      0.0,
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
      0.0,
      -0.0
    ],
    [
      0.0,
      -0.0
    ]
  ],
  "reason": "停车或低速等待；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      2.9,
      -0.02
    ],
    [
      5.7,
      -0.04
    ],
    [
      8.38,
      -0.06
    ],
    [
      10.91,
      -0.08
    ],
    [
      13.3,
      -0.1
    ],
    [
      15.51,
      -0.12
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[2.9, -0.02], [5.7, -0.04], [8.38, -0.06], [10.91, -0.08], [13.3, -0.1], [15.51, -0.12]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 20. 763dafaff2924e2899184c0cc9f3cfdc

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-07-24-11-22-45+0800__CAM_FRONT__1532402751662460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：9.438156697434662
- FDE：17.70709462334236
- 可能原因：左转样本较少，模型可能偏向训练集中更常见的 KEEP_LANE 或 STOP。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.87,
      -0.0
    ],
    [
      10.39,
      0.1
    ],
    [
      16.57,
      0.36
    ],
    [
      22.24,
      0.73
    ],
    [
      27.94,
      1.19
    ],
    [
      33.65,
      1.72
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      3.1,
      -0.01
    ],
    [
      6.03,
      -0.01
    ],
    [
      8.81,
      0.01
    ],
    [
      11.41,
      0.05
    ],
    [
      13.81,
      0.11
    ],
    [
      16.01,
      0.18
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[3.1, -0.01], [6.03, -0.01], [8.81, 0.01], [11.41, 0.05], [13.81, 0.11], [16.01, 0.18]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 21. 3a8e7003ede54b008ec4589adc8c9db8

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-08-02-17-28-51+0800__CAM_FRONT__1533202755162468.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：9.379183999828959
- FDE：16.702347140447056
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      5.67,
      0.01
    ],
    [
      11.13,
      0.04
    ],
    [
      16.02,
      0.07
    ],
    [
      21.21,
      0.11
    ],
    [
      26.34,
      0.18
    ],
    [
      31.5,
      0.27
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      3.0,
      -0.01
    ],
    [
      5.8,
      -0.01
    ],
    [
      8.38,
      -0.01
    ],
    [
      10.74,
      -0.01
    ],
    [
      12.88,
      -0.01
    ],
    [
      14.8,
      -0.01
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[3.0, -0.01], [5.8, -0.01], [8.38, -0.01], [10.74, -0.01], [12.88, -0.01], [14.8, -0.01]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 22. aafb3cca7c7d4ff0b96191814f9eb2ed

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-07-24-11-13-19+0800__CAM_FRONT__1532402423162460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：9.35412230466531
- FDE：17.080529851266327
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "TURN_RIGHT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.67,
      -0.07
    ],
    [
      9.3,
      -0.3
    ],
    [
      13.4,
      -0.61
    ],
    [
      17.87,
      -1.06
    ],
    [
      22.72,
      -1.7
    ],
    [
      27.17,
      -2.4
    ]
  ],
  "reason": "沿道路趋势向右行驶；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      2.2,
      -0.03
    ],
    [
      4.2,
      -0.09
    ],
    [
      6.01,
      -0.17
    ],
    [
      7.61,
      -0.26
    ],
    [
      9.01,
      -0.36
    ],
    [
      10.2,
      -0.46
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[2.2, -0.03], [4.2, -0.09], [6.01, -0.17], [7.61, -0.26], [9.01, -0.36], [10.2, -0.46]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 23. 348c1898febd43bb9c87c5bc112e72a1

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385315662404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：9.314008425792908
- FDE：16.412562261877337
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      1.56,
      0.02
    ],
    [
      3.08,
      0.11
    ],
    [
      4.49,
      0.21
    ],
    [
      5.79,
      0.31
    ],
    [
      7.11,
      0.44
    ],
    [
      8.19,
      0.55
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
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.1,
      0.01
    ],
    [
      8.2,
      0.08
    ],
    [
      12.3,
      0.21
    ],
    [
      16.4,
      0.39
    ],
    [
      20.5,
      0.61
    ],
    [
      24.6,
      0.84
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[4.1, 0.01], [8.2, 0.08], [12.3, 0.21], [16.4, 0.39], [20.5, 0.61], [24.6, 0.84]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 24. d8a9c9c7ef7e4f9cbc03f48f94b57370

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-07-18-11-50-34+0800__CAM_FRONT__1531885863012466.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：9.22906849028293
- FDE：15.542705684661215
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      1.96,
      0.02
    ],
    [
      4.14,
      0.08
    ],
    [
      6.39,
      0.19
    ],
    [
      8.6,
      0.33
    ],
    [
      10.77,
      0.53
    ],
    [
      12.92,
      0.8
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
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.81,
      0.01
    ],
    [
      9.6,
      0.06
    ],
    [
      14.38,
      0.14
    ],
    [
      19.1,
      0.24
    ],
    [
      23.8,
      0.36
    ],
    [
      28.46,
      0.51
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
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.81, 0.01], [9.6, 0.06], [14.38, 0.14], [19.1, 0.24], [23.8, 0.36], [28.46, 0.51]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 25. 1a1dc7ef4955481ba3755fbaa39a53d8

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-30-10-33-52-0400__CAM_FRONT__1535639693112404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：9.203385593803988
- FDE：14.41012491271328
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      1.15,
      -0.01
    ],
    [
      2.33,
      -0.04
    ],
    [
      3.69,
      -0.07
    ],
    [
      5.32,
      -0.11
    ],
    [
      7.38,
      -0.17
    ],
    [
      9.49,
      -0.21
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
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.1,
      -0.03
    ],
    [
      8.16,
      -0.06
    ],
    [
      12.18,
      -0.09
    ],
    [
      16.16,
      -0.11
    ],
    [
      20.08,
      -0.13
    ],
    [
      23.9,
      -0.15
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
{"action": "KEEP_LANE", "risk": "HIGH", "trajectory": [[4.1, -0.03], [8.16, -0.06], [12.18, -0.09], [16.16, -0.11], [20.08, -0.13], [23.9, -0.15]], "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"}
```

## 26. 1e65fa62bee34256809a762821cae323

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-07-24-11-13-19+0800__CAM_FRONT__1532402428112460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：9.032857431796696
- FDE：16.34237742802436
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "TURN_RIGHT",
  "risk": "MEDIUM",
  "trajectory": [
    [
      5.64,
      -0.11
    ],
    [
      10.84,
      -0.41
    ],
    [
      16.03,
      -0.89
    ],
    [
      20.77,
      -1.46
    ],
    [
      26.53,
      -2.41
    ],
    [
      31.93,
      -3.5
    ]
  ],
  "reason": "沿道路趋势向右行驶；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      3.0,
      -0.03
    ],
    [
      5.88,
      -0.06
    ],
    [
      8.61,
      -0.11
    ],
    [
      11.18,
      -0.16
    ],
    [
      13.61,
      -0.23
    ],
    [
      15.9,
      -0.32
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "MEDIUM", "trajectory": [[3.0, -0.03], [5.88, -0.06], [8.61, -0.11], [11.18, -0.16], [13.61, -0.23], [15.9, -0.32]], "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"}
```

## 27. 4f678fa48380438fa73e79931cc86e45

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-08-02-17-16-37+0800__CAM_FRONT__1533201732512460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：9.021221043524097
- FDE：15.209286636788724
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "STOP",
  "risk": "LOW",
  "trajectory": [
    [
      -0.0,
      0.0
    ],
    [
      -0.0,
      0.0
    ],
    [
      -0.0,
      0.0
    ],
    [
      -0.0,
      0.0
    ],
    [
      -0.0,
      0.0
    ],
    [
      0.0,
      0.0
    ]
  ],
  "reason": "停车或低速等待；周边交通参与者较少。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "TURN_RIGHT",
  "risk": "LOW",
  "trajectory": [
    [
      2.61,
      -0.15
    ],
    [
      5.2,
      -0.61
    ],
    [
      7.71,
      -1.38
    ],
    [
      10.1,
      -2.43
    ],
    [
      12.3,
      -3.71
    ],
    [
      14.3,
      -5.18
    ]
  ],
  "reason": "沿道路趋势向右行驶；周边交通参与者较少。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "TURN_RIGHT", "risk": "LOW", "trajectory": [[2.61, -0.15], [5.2, -0.61], [7.71, -1.38], [10.1, -2.43], [12.3, -3.71], [14.3, -5.18]], "reason": "沿道路趋势向右行驶；周边交通参与者较少。"}
```

## 28. ae94b61493d74e4ab194621a930441bd

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-08-02-17-16-37+0800__CAM_FRONT__1533201736412460.jpg`
- 错误类型：Action error, Large ADE, Large FDE
- ADE：8.887287178063483
- FDE：14.09408741281251
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "SLOW_DOWN",
  "risk": "LOW",
  "trajectory": [
    [
      0.0,
      -0.0
    ],
    [
      0.0,
      -0.0
    ],
    [
      0.04,
      0.0
    ],
    [
      0.37,
      0.0
    ],
    [
      1.22,
      0.0
    ],
    [
      2.68,
      0.01
    ]
  ],
  "reason": "降低速度并继续观察前方；周边交通参与者较少。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "TURN_RIGHT",
  "risk": "LOW",
  "trajectory": [
    [
      2.61,
      -0.16
    ],
    [
      5.3,
      -0.66
    ],
    [
      7.99,
      -1.51
    ],
    [
      10.6,
      -2.69
    ],
    [
      13.1,
      -4.21
    ],
    [
      15.4,
      -6.06
    ]
  ],
  "reason": "沿道路趋势向右行驶；周边交通参与者较少。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "TURN_RIGHT", "risk": "LOW", "trajectory": [[2.61, -0.16], [5.3, -0.66], [7.99, -1.51], [10.6, -2.69], [13.1, -4.21], [15.4, -6.06]], "reason": "沿道路趋势向右行驶；周边交通参与者较少。"}
```

## 29. a60efc88acd84c52b797f85499ae07e4

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n008-2018-08-27-11-48-51-0400__CAM_FRONT__1535385314162404.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：8.821291881387285
- FDE：16.286475984693556
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      1.97,
      0.06
    ],
    [
      3.84,
      0.24
    ],
    [
      5.53,
      0.51
    ],
    [
      7.06,
      0.86
    ],
    [
      8.52,
      1.25
    ],
    [
      9.88,
      1.64
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
  "action": "TURN_LEFT",
  "risk": "HIGH",
  "trajectory": [
    [
      4.1,
      0.04
    ],
    [
      8.3,
      0.28
    ],
    [
      12.61,
      0.73
    ],
    [
      17.0,
      1.38
    ],
    [
      21.5,
      2.19
    ],
    [
      26.1,
      3.11
    ]
  ],
  "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "TURN_LEFT", "risk": "HIGH", "trajectory": [[4.1, 0.04], [8.3, 0.28], [12.61, 0.73], [17.0, 1.38], [21.5, 2.19], [26.1, 3.11]], "reason": "沿道路趋势向左行驶；周边交通参与者密集，需要谨慎决策。"}
```

## 30. e06299dddfce465d90191d86e05a3f2b

- 图片：`/home/pc/datasets/Full_dataest/samples/CAM_FRONT/n015-2018-07-27-11-24-31+0800__CAM_FRONT__1532661912362460.jpg`
- 错误类型：Large ADE, Large FDE
- ADE：8.798558144288737
- FDE：15.349856676855325
- 可能原因：轨迹形状或速度尺度预测不准；若同时动作错误，离散决策错误会进一步放大轨迹误差。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "LOW",
  "trajectory": [
    [
      4.64,
      -0.07
    ],
    [
      9.78,
      -0.19
    ],
    [
      14.38,
      -0.33
    ],
    [
      18.9,
      -0.49
    ],
    [
      23.23,
      -0.68
    ],
    [
      27.34,
      -0.95
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者较少。"
}
```

### Parsed Prediction

```json
{
  "parse_success": true,
  "parser": "json",
  "action": "KEEP_LANE",
  "risk": "LOW",
  "trajectory": [
    [
      2.5,
      -0.03
    ],
    [
      4.8,
      -0.09
    ],
    [
      6.9,
      -0.16
    ],
    [
      8.8,
      -0.24
    ],
    [
      10.5,
      -0.32
    ],
    [
      12.0,
      -0.4
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者较少。",
  "action_valid": true,
  "risk_valid": true,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{"action": "KEEP_LANE", "risk": "LOW", "trajectory": [[2.5, -0.03], [4.8, -0.09], [6.9, -0.16], [8.8, -0.24], [10.5, -0.32], [12.0, -0.4]], "reason": "保持当前车道并平稳前进；周边交通参与者较少。"}
```
