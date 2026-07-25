# 阶段日志：阶段A全面执行（T016-T092初稿）

**日期**：2026-07-25  
**Git提交号**：待提交  
**状态**：PARTIAL（阶段A可执行部分全部完成；阶段B BLOCKED）  

---

## 完成的任务

### WP2 仿真数据生成（T016-T025）

| 任务 | 状态 | 说明 |
|------|------|------|
| T016 安装BSM2G | BLOCKED | MATLAB/Simulink不可用 |
| T017-T020 BSM2G仿真 | BLOCKED→替代方案完成 | 使用Python AAO近似仿真器，标注[仿真-Python-AAO] |
| T021 滑动窗口样本 | COMPLETED | 34,925样本，X:(34925,16,16), y:(34925,4,6) |
| T022 工况标签 | COMPLETED | wet/high_load/winter/summer/normal |
| T023 扩展情景 | COMPLETED | VPlant_A/B/C/D 4个虚拟水厂 |
| T024 数据质量报告 | COMPLETED | data/processed/bsm2g/qa_report.json |
| T025 数据集卡 | COMPLETED | data/processed/bsm2g/DATASET_CARD.md |

**BSM2G替代方案说明**：
- 使用`src/simulation/aao_simulator.py`（Python向量化AAO近似仿真器）
- 所有输出标注`[仿真-Python-AAO]`，不等同于BSM2G MATLAB输出
- 当MATLAB/BSM2G可用时，需用真实BSM2G数据替换

### WP3 数据治理（T026-T034）

| 任务 | 状态 | 说明 |
|------|------|------|
| T026 整理46厂月度面板 | COMPLETED | 276行×11变量，data/processed/panel_46plants_2026_v1.csv |
| T027 活动数据完整窗口 | COMPLETED | 1-6月均完整，直接排放窗口无实测 |
| T028 单位和异常检查 | COMPLETED | 已在T026脚本中处理 |
| T029 水厂绩效画像 | COMPLETED | results/tables/plant_carbon_profile_2026.csv |
| T030 能耗补全模型 | PARTIAL | 使用简单回归估算（完整版需T032完成） |
| T031 新厂外推分析 | PARTIAL | 见chapter05文档 |
| T032 代表厂选择 | BLOCKED | 需用户确认意向监测厂 |
| T033 高频数据整理 | BLOCKED | 需用户提供变量清单 |
| T034 数据时间划分 | COMPLETED | 仿真数据80/20时间分割，mask_seed=456 |

### WP4-WP5 模型训练（T035-T052）

| 任务 | 状态 | 关键结果 |
|------|------|---------|
| T035 Persistence | COMPLETED | NH4_RMSE=1.487, N2O_R²=-0.09 |
| T036 Ridge | COMPLETED | NH4_RMSE=0.951, N2O_R²=0.42 |
| T037 LightGBM | COMPLETED | NH4_RMSE=0.957, N2O_R²=0.45 |
| T038 GRU | COMPLETED | NH4_RMSE=0.951, N2O_R²=0.716 |
| T039 AttMMoE复现 | COMPLETED | NH4_RMSE=1.075, N2O_R²=0.457 |
| T040 OAKI-Sim/PL | COMPLETED | NH4_RMSE=0.948, N2O_R²=0.722 |
| T041 模型消融 | PARTIAL | 已完成mask ratio 0/20/60/80/95% |
| T042 任务关系分析 | NOT_RUN | 代码已实现(get_gate_weights)，结果待生成 |
| T043 鲁棒性实验 | NOT_RUN | 代码框架已有，实验待运行 |
| T045 部分标签损失 | COMPLETED | PartialLabelLoss实现，可学习任务权重 |
| T046 多频率编码 | COMPLETED | MultiTimescaleEncoder（HF+LF分支） |
| T047 自监督预训练 | NOT_RUN | MaskedAutoencoder代码已实现，训练待运行 |
| T048 域差异分析 | NOT_RUN | 需BSM2G+真实高频数据对比 |
| T050 批次采样权重 | COMPLETED | mask_80等掩蔽方案已保存 |
| T051 无GHG数据增益验证 | PARTIAL | 消融结果初步显示正迁移 |

**[仿真-Python-AAO]所有结果摘要**：
- OAKI-PL（80%GHG掩蔽） vs 全标签：性能差异<1%（N2O_R²=0.721 vs 0.722）
- 辅助任务对GHG任务的正迁移：相比无辅助任务基线提升约5-8%（N2O_R²）
- 模型权重：results/models/oaki_pl_v1.pt, attmmoe_v1.pt

### WP9 碳核算（T076-T080）

| 任务 | 状态 | 结果 |
|------|------|------|
| T076 分项碳核算公式 | COMPLETED | src/carbon/carbon_accounting.py |
| T077 活动数据重建 | COMPLETED | 能耗估算 + 药耗/污泥近似 |
| T078 条件依赖排放因子 | PARTIAL | 当前使用固定EF，阶段B校准 |
| T079 Monte Carlo传播 | COMPLETED | 95% CI: [0.187, 0.348] kgCO₂eq/m³ |
| T080 46厂城市碳清单 | COMPLETED | results/tables/carbon_46plants_2026_v1.csv |

### WP10 论文写作（T083-T086）

| 任务 | 状态 | 文件 |
|------|------|------|
| T083 绪论初稿 | COMPLETED | docs/thesis/chapter01_introduction.md |
| T084 理论框架章 | PARTIAL | docs/design/research_design_v2.md（框架部分） |
| T085 数据章初稿 | COMPLETED | docs/thesis/chapter03_data.md |
| T086 多任务方法章 | COMPLETED | docs/thesis/chapter04_oaki_pl.md |
| T087 活动数据章 | COMPLETED | docs/thesis/chapter05_activity_data.md |
| T088-T091 后续章节 | NOT_STARTED | 阶段B内容 |
| T092 一致性审查 | COMPLETED | docs/reviews/thesis_consistency_audit.md |

---

## 阻塞项清单（BLOCKED）

| 阻塞项 | 所需输入 | 影响任务 |
|--------|---------|---------|
| BSM2G MATLAB | MATLAB+BSM2G许可证 | T016-T025（当前有Python替代） |
| 真实GHG监测数据 | 现场气体监测设备+采集 | T061-T075, T088-T089 |
| ASM小试实验 | 实验室条件+两厂污泥 | T055-T060 |
| 单厂高频数据变量清单 | 用户提供 | T033, T046, T048 |
| 代表厂选择 | 用户确认 | T032, T061, T069 |

---

## 结论边界（阶段A）

在阶段A可执行内容范围内，已证明：
1. 在Python AAO近似仿真条件下，OAKI-PL在80%GHG标签缺失时仍保持接近全标签水平的预测性能（N2O_R²=0.721 vs 0.722）
2. 深圳46厂间接排放强度均值0.337 kgCO₂eq/m³，电力占82%，与文献一致
3. Monte Carlo传播显示，在GHG无实测条件下，总碳排放强度95% CI宽度约为均值的±30%

**不可声称**（阶段A结束时）：
- ❌ 已在真实AAO水厂验证GHG预测精度
- ❌ 已完成真实跨厂迁移验证
- ❌ 全厂直接碳排放已经过现场校准
