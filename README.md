# OAKI Project

## 稀缺GHG真值条件下融合机理仿真数据与真实运行数据的AAO污水处理厂全厂碳排放建模研究

**Carbon Emission Modeling for AAO Wastewater Treatment Plants Integrating Mechanistic Simulation Data and Real Operational Data under Scarce Greenhouse Gas Ground Truth**

> **版本**：V2.0（2026-07-25，OAKI框架重构版）  
> **状态**：阶段0完成（仓库审计与重构）；阶段A进行中

---

## 📌 研究概述

本研究围绕以下中心科学问题展开：

> **在GHG真值稀缺、运行数据标签不完整、不同污水厂运行条件存在域差异的情况下，如何融合机理仿真数据（BSM2G）、ASM知识和多时间尺度运行数据，建立可迁移、可校准、可解释并能够输出不确定性的AAO污水处理厂全厂碳排放模型？**

### 三个核心研究问题

- **RQ1**：无GHG标签的长期运行数据能否通过部分标签多任务学习提升GHG预测精度？
- **RQ2**：BSM2G和ASM提供的机理先验如何迁移到目标域，并控制负迁移？
- **RQ3**：新厂需要多少天GHG真值才能完成可靠概率校准？

### 三项核心贡献

| 贡献 | 方法 | 阶段A证据 |
|------|------|---------|
| **OAKI-PL** | 部分标签多任务过程状态学习 | BSM2G仿真+人工掩蔽实验 |
| **OAKI-Transfer** | 分层ASM参数迁移+厂级Adapter | 仿真域虚拟跨厂实验 |
| **OAKI-Cal/Carbon** | 概率GHG校准+全厂碳排放核算 | 仿真掩蔽实验+46厂活动数据 |

---

## ⚠️ 证据边界声明

本项目严格区分以下数据层级：

| 标识 | 描述 | 允许的声明强度 |
|------|------|--------------|
| `[仿真]` | BSM2G机理仿真输出 | "在仿真条件下有效" |
| `[文献先验]` | 基于文献参数范围 | "与文献报道范围一致" |
| `[真实活动数据]` | 46厂月度数据（不含GHG） | "在活动数据层面有效" |
| `[真实GHG]` | 实测N₂O/CH₄通量（阶段B） | "在现场观测条件下验证" |
| `[小试]` | 实验室动力学参数（阶段B） | "在小试批次中可辨识" |

**禁止**：将BSM2G输出的GHG写成现场真值；将虚拟水厂写成两个真实水厂。

---

## 📁 项目结构

```
OAKI-project/
├── README.md                         # 项目总览
├── DATA_POLICY.md                    # 数据保密与版本策略
├── environment.yml                   # Conda环境（Python+ML）
├── requirements.txt                  # pip依赖
├── configs/                          # 实验配置文件
├── data/
│   ├── raw/                          # 原始数据（不提交敏感数据）
│   ├── interim/                      # 中间处理数据
│   ├── processed/
│   │   └── bsm2g/                    # BSM2G仿真数据集（BLOCKED，待获取BSM2G）
│   └── schema/                       # 数据字典
├── src/
│   ├── data/                         # 数据预处理
│   ├── simulation/                   # BSM2G接口与数据导出
│   ├── models/                       # OAKI-PL/Transfer/Cal模型
│   ├── asm/                          # ASM参数管理与约束
│   ├── calibration/                  # 概率校准模块
│   ├── carbon/                       # 全厂碳核算（含原FPCM M1-M6）
│   └── evaluation/                   # 评估指标与可视化
├── scripts/                          # 运行脚本
├── tests/                            # 单元测试
├── results/
│   ├── models/                       # 模型权重
│   ├── tables/                       # 结果表格
│   ├── figures/                      # 图表
│   └── manifests/                    # 结果清单
├── docs/
│   ├── thesis/                       # 论文各章草稿
│   ├── design/                       # 研究设计文档
│   │   ├── research_design_v2.md     # 博士论文研究设计V2.0
│   │   ├── thesis_outline_v2.md      # 论文大纲V2.0
│   │   ├── task_mapping.csv          # 修订后任务清单
│   │   └── claim_evidence_matrix.csv # 研究问题-方法-证据映射矩阵
│   ├── reviews/
│   │   └── taskbook_audit.md         # 任务书完备性审查报告
│   ├── datasets/                     # 数据集卡
│   ├── protocols/                    # 实验协议
│   └── logs/
│       └── template.md               # 阶段日志模板
├── paper/                            # 论文草稿（原FPCM框架，待重构）
└── releases/                         # 发布包
```

---

## 🚦 当前状态

| 阶段 | 名称 | 状态 |
|------|------|------|
| 阶段0 | 仓库审计与重构 | ✅ IN_PROGRESS |
| 阶段1 | 任务书审阅与研究设计重构 | ✅ IN_PROGRESS |
| 阶段2 | 系统文献调研 | ⏳ 待开始 |
| **BSM2G安装** | **关键阻塞项** | **⛔ BLOCKED（需用户确认MATLAB/BSM2G）** |
| 阶段3 | BSM2G仿真与数据生成 | ⛔ BLOCKED |
| 阶段4 | 仿真历史数据与标签掩蔽 | ⛔ BLOCKED |
| 阶段5 | 基线模型 | ⛔ BLOCKED（依赖BSM2G数据） |
| 阶段5A | 46厂活动数据分析 | ✅ 可立即开始 |
| 阶段6+ | OAKI-PL/Transfer/Cal | ⛔ BLOCKED（依赖BSM2G） |

---

## 🔑 需要用户提供的关键输入

1. **BSM2G**：MATLAB版本？BSM2G获取渠道（官方网站/文献作者/已有许可证）？
2. **高频数据**：单厂2小时过程数据的变量清单、时间段和文件位置
3. **代表厂**：是否已有意向的两座深度监测厂？
4. **GHG监测计划**：预计何时可以开展现场N₂O/CH₄监测？

---

## 📝 版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| v0.1 | 2026-07-25 | 阶段0完成：仓库审计、OAKI框架重构、任务书审查报告 |
| v0.0 | 2026-07-21 | 原FPCM v3.0草稿（8章，轻量化数据框架） |

---

## 🔗 关键文档

- [任务书完备性审查报告](docs/reviews/taskbook_audit.md)
- [博士论文研究设计V2.0](docs/design/research_design_v2.md)
- [论文大纲V2.0](docs/design/thesis_outline_v2.md)
- [修订后任务清单](docs/design/task_mapping.csv)
- [研究问题-证据映射矩阵](docs/design/claim_evidence_matrix.csv)
- [数据保密策略](DATA_POLICY.md)

---

*最后更新：2026-07-25（阶段0：仓库审计与OAKI框架重构）*
