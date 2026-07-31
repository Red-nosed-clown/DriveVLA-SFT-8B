# 失败分析

评估脚本会自动为每条失败预测标记一种或多种错误：

- `Invalid output format`：输出无法解析为规定结构；
- `Action error`：动作分类错误；
- `Risk error`：风险等级错误；
- `Trajectory parse failure`：轨迹不是六个有限二维点；
- `Large ADE`：ADE 不小于 5 米；
- `Large FDE`：FDE 不小于 8 米。

`scripts/analyze_failures.py` 会优先展示轨迹误差较大的样本，并保留原图路径、
真实答案、解析后预测和原始模型文本。这样可以区分三类问题：

1. 模型理解场景失败；
2. 模型知道大致答案，但 JSON 格式不稳定；
3. Action 正确，但连续轨迹数值误差较大。

`scripts/visualize_trajectory.py` 在左侧显示 `CAM_FRONT` 图像，右侧绘制当前
自车坐标系下的 Ground Truth 与 Prediction。横轴是 lateral，纵轴是 forward，
图标题同时显示 Action、Risk、ADE 和 FDE。

nuScenes-mini 只有 10 个 scene，验证集规模很小。失败分析适合展示工程闭环和
发现问题的能力，不应把这组离线结果描述为真实道路闭环控制能力。

## nuScenes-mini 实验观察

- Base 34 条全部不满足严格枚举格式，但六点轨迹有效率为 100%；
- QLoRA 34 条全部能解析为规定 JSON；
- QLoRA 仍有 25 条至少命中一种错误，其中常见问题是 Action error；
- QLoRA 预测动作分布为 KEEP_LANE 21 条、STOP 13 条，没有预测 TURN_LEFT；
- 验证集真实动作包含 KEEP_LANE 23 条、TURN_LEFT 10 条、SLOW_DOWN 1 条。

这说明 QLoRA 已明显学会输出协议和风险规则，也改善了轨迹误差，但小数据下动作
决策出现类别塌缩。后续优先方案是扩展数据、保证验证 scene 类别覆盖，并对稀有
动作做重采样或加权，而不是只继续增加当前 344 条数据的训练 epoch。

## Trainval 完整验证集实验观察

扩展到本地 trainval 后，验证集共有 2319 条样本。QLoRA adapter 的完整评估结果为：

- Parse Success：99.83%；
- Action Accuracy：80.42%；
- Risk Accuracy：95.34%；
- Trajectory Valid：99.83%；
- ADE：2.2574 m；
- FDE：3.9219 m。

这说明 mini 阶段最明显的动作类别塌缩已经缓解：模型不再只输出 KEEP_LANE 或 STOP，
TURN_LEFT 和 TURN_RIGHT 也有较高召回。但新的主要问题变成了两类：

1. `SLOW_DOWN` 仍然很弱，验证集 63 条中只预测正确 8 条，说明当前动作标签规则和样本
   占比都不够稳定；
2. 轨迹形状偏平滑。GT 平均弯曲度为 0.2023，预测平均弯曲度只有 0.1085；
   TURN_LEFT / TURN_RIGHT 的预测横向位移也小于真实值。

因此，下一阶段不应简单把 epoch 从 3 增加到更多。更优先的方向是：先改进评估指标，
再改进动作标签和采样策略，最后再考虑加入历史运动状态、多相机或地图信息。

真实失败文档：

- `results/base_failure_analysis.md`
- `results/finetuned_failure_analysis.md`
- `results/trainval_finetuned_full_failure_analysis.md`
- `results/trainval_finetuned_full_trajectory_geometry.md`
