# Base 与 QLoRA 对比

- 验证样本数：34
- ADE/FDE 只在成功解析出六点轨迹的样本上计算。

| Metric | Base | QLoRA |
|---|---:|---:|
| Parse Success | 0.00% | 100.00% |
| Action Accuracy | 0.00% | 47.06% |
| Risk Accuracy | 0.00% | 79.41% |
| Trajectory Valid | 100.00% | 100.00% |
| ADE (m) | 5.7259 | 2.9181 |
| FDE (m) | 9.7330 | 5.5081 |

- Base 失败样本：34
- QLoRA 失败样本：25
- ADE 相对降低：49.04%
- FDE 相对降低：43.41%
