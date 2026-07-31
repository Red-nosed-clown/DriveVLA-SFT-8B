# DriveVLA v5 DPO Pilot 总结

## 实验设置

- 最终验证集：v5 scene 隔离验证集的前 200 条；
- 偏好候选：从 SFT train split 分层抽样 512 条；
- 可用偏好对：372 条，按 scene 划分为 336 train / 36 val；
- 训练：Qwen3-VL-8B，4bit QLoRA DPO，1 epoch，84 optimizer steps；
- 公平基线：合并后的 v5 SFT 以同一 4bit 和 greedy 参数推理。

最终验证样本没有参与候选抽样、偏好构造或 DPO train/val。

## 结果

| Model | Preference Acc | Action Acc | ADE (m) | FDE (m) | Line-like |
|---|---:|---:|---:|---:|---:|
| merged SFT | - | 64.00% | 0.8371 | 1.8579 | 41.00% |
| DPO full-output rejected | 97.22% | 63.50% | 0.8439 | 1.8895 | 35.50% |
| DPO isolated-field rejected | 94.44% | 64.00% | 0.8477 | 1.8797 | 42.00% |

完整输出版在 200 条中 ADE 改善 85 条、持平 12 条、退化 103 条。单字段版
改善 75 条、持平 43 条、退化 82 条。两者都没有通过总体 Action Accuracy、
ADE 和 FDE 不退化的放大门槛。

## 分析

- DPO preference accuracy 只衡量 chosen 的相对 log-prob，不能替代驾驶指标；
- 两版对 TURN_LEFT/RIGHT 的 ADE/FDE 有小幅改善，但 SLOW_DOWN 明显退化；
- 单字段 rejected 消除了多字段 credit assignment 混淆，但 336 对数据仍不足以
  获得独立验证收益；
- full-output 版降低了近似直线比例，但 ADE/FDE 同时变差，说明“更弯”不等于
  “更接近真实轨迹”；
- 该流程是离线偏好优化，不是带环境反馈的闭环强化学习。

## 决策

保留 v5 SFT 作为当前主模型，不用 pilot DPO adapter 替换它。下一轮先扩大到
4000 个无泄漏候选，继续使用单字段 rejected，并在训练前审计各失败类别和 GT
action 分布。只有 200 条 pilot 同时满足 Action Accuracy、ADE、FDE 不退化，
并且 SLOW_DOWN 与转弯子集至少一项明确改善，才运行全部 2115 条验证。
