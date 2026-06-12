# 简历与答辩笔记

## 项目名称

DriveVLA-SFT-8B：基于 Qwen3-VL-8B 与 QLoRA 的自动驾驶 VLA 微调

## 简历 Bullet

- 基于 `nuScenes-mini` 的 `CAM_FRONT` 图像、ego pose 与目标标注构建
  344 条视觉-语言-动作 SFT 数据，将未来 6 个 ego pose 转换为当前自车
  坐标系下的 `[forward_m, lateral_m]` 轨迹，并按 scene 隔离训练集与验证集。
- 在单卡 RTX 5090 上使用 LLaMA-Factory 和 NF4 4bit QLoRA 微调
  `Qwen3-VL-8B-Instruct`，配置 LoRA rank 16、bf16、梯度累积与
  assistant-only 监督，输出 Action、heuristic Risk、六点轨迹和 Reason。
- 自行实现生成结果的多级 JSON 容错解析、Action/Risk Accuracy、轨迹
  ADE/FDE、可视化和失败案例分类，并对比基座模型与 QLoRA adapter。
- 编写单卡小数据教学版训练脚本，展示多模态 processor、chat template、
  assistant-only loss mask、BitsAndBytes NF4 加载和 PEFT adapter 保存原理。

真实验证结果：Parse Success 从 0% 提升至 100%，Action Accuracy 47.06%，
Risk Accuracy 79.41%，ADE 从 5.7259 m 降至 2.9181 m，FDE 从 9.7330 m
降至 5.5081 m。简历中同时保留“34 条单 scene 验证集”的口径，避免夸大。

## 面试讲解主线

1. 为什么是 VLA：任务不仅描述图像，还要求输出离散驾驶动作和连续未来轨迹。
2. 标签怎么来：沿 nuScenes `sample.next` 找未来关键帧，再用当前 ego yaw
   把世界坐标变换到当前自车坐标系，不能直接拿世界坐标当 forward/lateral。
3. 为什么按 scene 切分：随机打散相邻帧会让几乎相同的连续图像泄漏到验证集。
4. 为什么是 QLoRA：4bit 保存冻结基座权重，LoRA 只更新低秩矩阵，使 8B
   多模态模型可以在 32 GB 单卡上真实反向传播。
5. 为什么自写评估：训练 loss 不能说明输出能否被下游系统使用，必须同时看
   JSON 可解析率、分类准确率、轨迹有效率和 ADE/FDE。
6. 项目边界是什么：Risk 是弱规则标签；mini 数据只有 10 个 scene；当前
   是离线生成评估，不等于真实车辆或仿真器中的闭环控制。

## 可继续增强的方向

- 扩展完整 nuScenes trainval，并重新设计覆盖各动作类别的 scene 级验证集。
- 从单前视图扩展到六视图，提升侧后方目标与路口场景的信息完整性。
- 使用类别重采样或加权 loss 缓解 KEEP_LANE、HIGH risk 的类别不均衡。
- 接入 CARLA 或规划控制器，评估碰撞率、到达率和闭环轨迹偏差。
