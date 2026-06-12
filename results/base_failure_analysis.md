# DriveVLA 失败案例分析

- 失败样本总数：34
- 展示样本数：20

## 1. a5c0ec90615e42818962e4e002de0cef

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800863412460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：15.014020533467576
- FDE：24.901254988453893
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      5.41,
      -0.05
    ],
    [
      11.0,
      -0.09
    ],
    [
      16.78,
      -0.13
    ],
    [
      22.77,
      -0.15
    ],
    [
      28.86,
      -0.19
    ],
    [
      35.1,
      -0.25
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      10.0,
      0.0
    ],
    [
      20.0,
      0.0
    ],
    [
      30.0,
      0.0
    ],
    [
      40.0,
      0.0
    ],
    [
      50.0,
      0.0
    ],
    [
      60.0,
      0.0
    ]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，中等风险因存在行人和车辆交叉干扰。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [10.0, 0.0],
    [20.0, 0.0],
    [30.0, 0.0],
    [40.0, 0.0],
    [50.0, 0.0],
    [60.0, 0.0]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，中等风险因存在行人和车辆交叉干扰。"
}
```

## 2. 49dfd2f2fef447cc9b8dec3e17c1c919

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800861912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：12.767393740138097
- FDE：22.851595130318586
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      1.5,
      0.0
    ],
    [
      3.0,
      0.0
    ],
    [
      4.5,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      7.5,
      0.0
    ],
    [
      9.0,
      0.0
    ]
  ],
  "reason": "前方有行人和车辆，需保持安全距离，中等风险因行人横穿和对向车流。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [1.5, 0.0],
    [3.0, 0.0],
    [4.5, 0.0],
    [6.0, 0.0],
    [7.5, 0.0],
    [9.0, 0.0]
  ],
  "reason": "前方有行人和车辆，需保持安全距离，中等风险因行人横穿和对向车流。"
}
```

## 3. f65ffdc408fb4a0c8ef0d1614b47dce8

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800853412460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：12.48009373951577
- FDE：19.199856770299096
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      2.03,
      4.19
    ],
    [
      4.06,
      8.38
    ],
    [
      6.09,
      12.57
    ],
    [
      8.12,
      16.76
    ],
    [
      10.15,
      20.95
    ],
    [
      12.18,
      25.14
    ]
  ],
  "reason": "前方有行人横穿马路，需减速避让；右侧有车辆正在变道，需保持安全距离；左侧有车辆正在驶入路口，需注意避让。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [2.03, 4.19],
    [4.06, 8.38],
    [6.09, 12.57],
    [8.12, 16.76],
    [10.15, 20.95],
    [12.18, 25.14]
  ],
  "reason": "前方有行人横穿马路，需减速避让；右侧有车辆正在变道，需保持安全距离；左侧有车辆正在驶入路口，需注意避让。"
}
```

## 4. f90292e4cdf647e1a8842baabdaafcec

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800860912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：11.655818075929234
- FDE：20.822019594650275
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.61,
      -0.03
    ],
    [
      9.33,
      -0.06
    ],
    [
      14.12,
      -0.09
    ],
    [
      19.14,
      -0.15
    ],
    [
      24.41,
      -0.2
    ],
    [
      29.82,
      -0.29
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      1.5,
      0.0
    ],
    [
      3.0,
      0.0
    ],
    [
      4.5,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      7.5,
      0.0
    ],
    [
      9.0,
      0.0
    ]
  ],
  "reason": "前方有行人和车辆，需保持安全距离，中等风险因行人靠近和车流存在。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [1.5, 0.0],
    [3.0, 0.0],
    [4.5, 0.0],
    [6.0, 0.0],
    [7.5, 0.0],
    [9.0, 0.0]
  ],
  "reason": "前方有行人和车辆，需保持安全距离，中等风险因行人靠近和车流存在。"
}
```

## 5. f77ef1c17cbf432587d705c88ce76b3b

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800848412460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：10.15570034107477
- FDE：15.732005593693387
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      0.08,
      -0.0
    ],
    [
      0.27,
      -0.0
    ],
    [
      0.72,
      -0.0
    ],
    [
      1.47,
      -0.01
    ],
    [
      2.47,
      -0.03
    ],
    [
      3.76,
      -0.06
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.22,
      -3.29
    ],
    [
      6.44,
      -2.21
    ],
    [
      9.66,
      -1.13
    ],
    [
      12.88,
      0.0
    ],
    [
      16.1,
      1.13
    ],
    [
      19.32,
      2.26
    ]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，避免碰撞。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "高",
  "trajectory": [
    [3.22, -3.29],
    [6.44, -2.21],
    [9.66, -1.13],
    [12.88, 0.0],
    [16.1, 1.13],
    [19.32, 2.26]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，避免碰撞。"
}
```

## 6. 9cc9718713c14974b5e3094e1c4eae1c

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800862912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：8.906028485106518
- FDE：16.13163971826795
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      5.27,
      -0.03
    ],
    [
      10.68,
      -0.08
    ],
    [
      16.27,
      -0.12
    ],
    [
      22.04,
      -0.16
    ],
    [
      28.04,
      -0.19
    ],
    [
      34.13,
      -0.23
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.0,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      9.0,
      0.0
    ],
    [
      12.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      18.0,
      0.0
    ]
  ],
  "reason": "前方存在行人和车辆，需保持安全距离，中等风险因行人靠近车道，需持续监控周围环境。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [3.0, 0.0],
    [6.0, 0.0],
    [9.0, 0.0],
    [12.0, 0.0],
    [15.0, 0.0],
    [18.0, 0.0]
  ],
  "reason": "前方存在行人和车辆，需保持安全距离，中等风险因行人靠近车道，需持续监控周围环境。"
}
```

## 7. 7d82aa0c679141d1a71733b85fdcd3ed

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800855412460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：8.567067577151505
- FDE：14.005855918150807
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      5.0,
      0.0
    ],
    [
      10.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      20.0,
      0.0
    ],
    [
      25.0,
      0.0
    ],
    [
      30.0,
      0.0
    ]
  ],
  "reason": "前方道路有较多车辆和行人，需保持安全距离，注意避让，中等风险主要因行人密集和车流复杂。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [5.0, 0.0],
    [10.0, 0.0],
    [15.0, 0.0],
    [20.0, 0.0],
    [25.0, 0.0],
    [30.0, 0.0]
  ],
  "reason": "前方道路有较多车辆和行人，需保持安全距离，注意避让，中等风险主要因行人密集和车流复杂。"
}
```

## 8. 648fe1aeca944fb793b334cb6ee01854

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800849412460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：7.4334514808000325
- FDE：11.770344090127526
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.0,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      9.0,
      0.0
    ],
    [
      12.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      18.0,
      0.0
    ]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，中等风险因周围存在多个行人和车辆，需谨慎驾驶。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [3.0, 0.0],
    [6.0, 0.0],
    [9.0, 0.0],
    [12.0, 0.0],
    [15.0, 0.0],
    [18.0, 0.0]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，中等风险因周围存在多个行人和车辆，需谨慎驾驶。"
}
```

## 9. 07175443e8444b8c8c4802fd004e33c1

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800855912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：7.324381043499617
- FDE：11.6020558523048
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      5.0,
      0.0
    ],
    [
      10.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      20.0,
      0.0
    ],
    [
      25.0,
      0.0
    ],
    [
      30.0,
      0.0
    ]
  ],
  "reason": "前方道路有车辆和行人，需保持安全距离，注意避让，中等风险因存在多辆车辆和行人，需谨慎驾驶。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [5.0, 0.0],
    [10.0, 0.0],
    [15.0, 0.0],
    [20.0, 0.0],
    [25.0, 0.0],
    [30.0, 0.0]
  ],
  "reason": "前方道路有车辆和行人，需保持安全距离，注意避让，中等风险因存在多辆车辆和行人，需谨慎驾驶。"
}
```

## 10. 98fa81992fb04e799c329eca220e7164

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800861412460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：6.927405041425848
- FDE：12.801890485393164
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.0,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      9.0,
      0.0
    ],
    [
      12.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      18.0,
      0.0
    ]
  ],
  "reason": "前方有行人和车辆，需保持安全距离，中等风险因行人横穿和对向车流。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [3.0, 0.0],
    [6.0, 0.0],
    [9.0, 0.0],
    [12.0, 0.0],
    [15.0, 0.0],
    [18.0, 0.0]
  ],
  "reason": "前方有行人和车辆，需保持安全距离，中等风险因行人横穿和对向车流。"
}
```

## 11. 056becbc0d5a46da8d59eebddedb47bb

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800856412460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：6.445479365551842
- FDE：9.661107596958022
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      5.0,
      0.0
    ],
    [
      10.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      20.0,
      0.0
    ],
    [
      25.0,
      0.0
    ],
    [
      30.0,
      0.0
    ]
  ],
  "reason": "前方道路有车辆和行人，需保持安全距离，中等风险因存在潜在行人和车辆交互。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [5.0, 0.0],
    [10.0, 0.0],
    [15.0, 0.0],
    [20.0, 0.0],
    [25.0, 0.0],
    [30.0, 0.0]
  ],
  "reason": "前方道路有车辆和行人，需保持安全距离，中等风险因存在潜在行人和车辆交互。"
}
```

## 12. 07c29094cb6144aa889c16c52f762d79

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800851912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：5.919028372937322
- FDE：10.388960486978474
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.0,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      9.0,
      0.0
    ],
    [
      12.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      18.0,
      0.0
    ]
  ],
  "reason": "前方存在大量行人和车辆，需保持安全距离，减速慢行，注意避让行人，确保安全通过。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "高",
  "trajectory": [
    [3.0, 0.0],
    [6.0, 0.0],
    [9.0, 0.0],
    [12.0, 0.0],
    [15.0, 0.0],
    [18.0, 0.0]
  ],
  "reason": "前方存在大量行人和车辆，需保持安全距离，减速慢行，注意避让行人，确保安全通过。"
}
```

## 13. 3b594831ff7f4e27a9889c7b7d0d8e92

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800850912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：5.836648913050371
- FDE：10.088746205550024
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.0,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      9.0,
      0.0
    ],
    [
      12.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      18.0,
      0.0
    ]
  ],
  "reason": "前方有大量行人和车辆，需保持安全距离，减速慢行，避免突然变道或急刹，以应对潜在的行人横穿或车辆变道风险。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "高",
  "trajectory": [
    [3.0, 0.0],
    [6.0, 0.0],
    [9.0, 0.0],
    [12.0, 0.0],
    [15.0, 0.0],
    [18.0, 0.0]
  ],
  "reason": "前方有大量行人和车辆，需保持安全距离，减速慢行，避免突然变道或急刹，以应对潜在的行人横穿或车辆变道风险。"
}
```

## 14. a84f43c4ef52461d940a6c7d0768b86f

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800859912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：5.475465760606557
- FDE：9.998004800959038
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "MEDIUM",
  "trajectory": [
    [
      4.37,
      -0.04
    ],
    [
      8.85,
      -0.09
    ],
    [
      13.47,
      -0.16
    ],
    [
      18.18,
      -0.23
    ],
    [
      22.97,
      -0.3
    ],
    [
      27.99,
      -0.4
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边存在一定数量的交通参与者。"
}
```

### Parsed Prediction

```json
{
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.0,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      9.0,
      0.0
    ],
    [
      12.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      18.0,
      0.0
    ]
  ],
  "reason": "前方道路有车辆和行人，需保持安全距离，中等风险因存在潜在行人和车辆交互。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [3.0, 0.0],
    [6.0, 0.0],
    [9.0, 0.0],
    [12.0, 0.0],
    [15.0, 0.0],
    [18.0, 0.0]
  ],
  "reason": "前方道路有车辆和行人，需保持安全距离，中等风险因存在潜在行人和车辆交互。"
}
```

## 15. 95c0a92d52584756832ec795d346e296

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800854412460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：5.312472260218849
- FDE：9.834886882928547
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.0,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      9.0,
      0.0
    ],
    [
      12.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      18.0,
      0.0
    ]
  ],
  "reason": "前方存在大量车辆和行人，需保持安全距离，谨慎驾驶。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "高",
  "trajectory": [
    [3.0, 0.0],
    [6.0, 0.0],
    [9.0, 0.0],
    [12.0, 0.0],
    [15.0, 0.0],
    [18.0, 0.0]
  ],
  "reason": "前方存在大量车辆和行人，需保持安全距离，谨慎驾驶。"
}
```

## 16. 77fc24547ab34182a945eecb825b6576

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800848912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE
- ADE：5.125115288898185
- FDE：7.560423268574319
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      2.1,
      0.0
    ],
    [
      4.2,
      0.0
    ],
    [
      6.3,
      0.0
    ],
    [
      8.4,
      0.0
    ],
    [
      10.5,
      0.0
    ],
    [
      12.6,
      0.0
    ]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，中等风险因周围有大量行人和车辆，需谨慎驾驶。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [2.1, 0.0],
    [4.2, 0.0],
    [6.3, 0.0],
    [8.4, 0.0],
    [10.5, 0.0],
    [12.6, 0.0]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，中等风险因周围有大量行人和车辆，需谨慎驾驶。"
}
```

## 17. 273c930b3f384bd58b2bbae02fe81d1e

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800859412460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large ADE, Large FDE
- ADE：5.0128236494096425
- FDE：9.182635787180061
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.2,
      -0.02
    ],
    [
      8.57,
      -0.04
    ],
    [
      13.06,
      -0.07
    ],
    [
      17.67,
      -0.12
    ],
    [
      22.39,
      -0.17
    ],
    [
      27.18,
      -0.22
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.0,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      9.0,
      0.0
    ],
    [
      12.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      18.0,
      0.0
    ]
  ],
  "reason": "前方道路有车辆和行人，需保持安全距离，中等风险因存在潜在行人和车辆交互。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [3.0, 0.0],
    [6.0, 0.0],
    [9.0, 0.0],
    [12.0, 0.0],
    [15.0, 0.0],
    [18.0, 0.0]
  ],
  "reason": "前方道路有车辆和行人，需保持安全距离，中等风险因存在潜在行人和车辆交互。"
}
```

## 18. 6cb024831cce4b6e8acf85afb7cece6e

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800858862460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large FDE
- ADE：4.878466416914264
- FDE：8.78036445712819
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

### Ground Truth

```json
{
  "action": "KEEP_LANE",
  "risk": "HIGH",
  "trajectory": [
    [
      4.4,
      -0.02
    ],
    [
      8.6,
      -0.01
    ],
    [
      12.97,
      -0.01
    ],
    [
      17.45,
      -0.03
    ],
    [
      22.07,
      -0.05
    ],
    [
      26.78,
      -0.08
    ]
  ],
  "reason": "保持当前车道并平稳前进；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      3.0,
      0.0
    ],
    [
      6.0,
      0.0
    ],
    [
      9.0,
      0.0
    ],
    [
      12.0,
      0.0
    ],
    [
      15.0,
      0.0
    ],
    [
      18.0,
      0.0
    ]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，中等风险因存在潜在行人和车辆交互。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [3.0, 0.0],
    [6.0, 0.0],
    [9.0, 0.0],
    [12.0, 0.0],
    [15.0, 0.0],
    [18.0, 0.0]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，中等风险因存在潜在行人和车辆交互。"
}
```

## 19. 0915646e387b484785ae2b847ffdee2f

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800853912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error, Large FDE
- ADE：4.65384831526748
- FDE：9.198070449828052
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

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
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      2.5,
      0.0
    ],
    [
      5.0,
      0.0
    ],
    [
      7.5,
      0.0
    ],
    [
      10.0,
      0.0
    ],
    [
      12.5,
      0.0
    ],
    [
      15.0,
      0.0
    ]
  ],
  "reason": "前方有行人横穿马路，需减速避让；右侧有车辆和行人，需保持安全距离；左侧有车辆，需注意避让。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "中等",
  "trajectory": [
    [2.5, 0.0],
    [5.0, 0.0],
    [7.5, 0.0],
    [10.0, 0.0],
    [12.5, 0.0],
    [15.0, 0.0]
  ],
  "reason": "前方有行人横穿马路，需减速避让；右侧有车辆和行人，需保持安全距离；左侧有车辆，需注意避让。"
}
```

## 20. e6b0b282aa174a978272dc2d0a89d560

- 图片：`/home/pc/datasets/nuscenes/samples/CAM_FRONT/n015-2018-11-21-19-38-26+0800__CAM_FRONT__1542800847912460.jpg`
- 错误类型：Invalid output format, Action error, Risk error
- ADE：4.130358985005236
- FDE：5.13008771854829
- 可能原因：模型没有稳定遵守枚举值或 JSON 结构，需要加强格式监督或约束解码。

### Ground Truth

```json
{
  "action": "SLOW_DOWN",
  "risk": "HIGH",
  "trajectory": [
    [
      0.08,
      -0.0
    ],
    [
      0.15,
      -0.0
    ],
    [
      0.35,
      -0.01
    ],
    [
      0.8,
      -0.01
    ],
    [
      1.54,
      -0.02
    ],
    [
      2.55,
      -0.03
    ]
  ],
  "reason": "降低速度并继续观察前方；周边交通参与者密集，需要谨慎决策。"
}
```

### Parsed Prediction

```json
{
  "parse_success": false,
  "parser": "json",
  "action": "UNKNOWN",
  "risk": "UNKNOWN",
  "trajectory": [
    [
      1.28,
      -2.84
    ],
    [
      2.56,
      -2.28
    ],
    [
      3.84,
      -1.72
    ],
    [
      5.12,
      -1.16
    ],
    [
      6.4,
      -0.6
    ],
    [
      7.68,
      0.0
    ]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，避免碰撞。",
  "action_valid": false,
  "risk_valid": false,
  "trajectory_valid": true
}
```

### Raw Prediction

```text
{
  "action": "安全沿道路行驶",
  "risk": "高",
  "trajectory": [
    [1.28, -2.84],
    [2.56, -2.28],
    [3.84, -1.72],
    [5.12, -1.16],
    [6.4, -0.6],
    [7.68, 0.0]
  ],
  "reason": "前方有车辆和行人，需保持安全距离，避免碰撞。"
}
```
