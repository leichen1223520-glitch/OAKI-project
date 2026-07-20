# AAO工艺污水处理厂轻量化数据下的全厂碳排放模型构建研究

> **OAKI Project** — Carbon Emission Modeling for AAO Wastewater Treatment Plants under Lightweight Data

---

## 📌 研究概述

本研究聚焦于 **AAO（厌氧-缺氧-好氧）工艺污水处理厂** 在轻量化数据条件下的全厂碳排放模型构建，探索在监测数据有限的实际场景中，如何建立准确、可靠的碳排放核算与预测体系。

### 核心问题
1. 如何在监测数据稀缺的条件下，构建完整的全厂碳排放模型？
2. AAO工艺各单元（厌氧池、缺氧池、好氧池、二沉池、污泥处理）的碳排放贡献如何量化？
3. 轻量化数据驱动模型与全量监测模型的精度差异如何评估？

---

## 🏗️ 研究阶段规划

| 阶段 | 名称 | 内容 | 状态 |
|------|------|------|------|
| Phase 1 | 文献综述与理论框架 | 碳排放核算方法、AAO工艺特征梳理 | 🔄 进行中 |
| Phase 2 | 数据需求分析与轻量化策略 | 关键参数识别、缺失数据处理方案 | ⏳ 待开始 |
| Phase 3 | 碳排放子模型构建 | 各处理单元碳排放机理模型 | ⏳ 待开始 |
| Phase 4 | 全厂集成模型开发 | 模型集成、参数率定、验证 | ⏳ 待开始 |
| Phase 5 | 灵敏度分析与不确定性评估 | 轻量化数据条件下的模型鲁棒性 | ⏳ 待开始 |
| Phase 6 | 案例应用与结果分析 | 实际污水处理厂验证 | ⏳ 待开始 |

---

## 📁 项目结构

```
OAKI-project/
├── README.md                    # 项目总览
├── CHANGELOG.md                 # 版本变更日志
├── docs/
│   ├── research_plan.md         # 详细研究计划
│   ├── literature/              # 文献笔记
│   └── phase_logs/              # 各阶段工作日志
├── data/
│   ├── raw/                     # 原始数据
│   ├── processed/               # 处理后数据
│   └── schema/                  # 数据字典
├── src/
│   ├── preprocessing/           # 数据预处理模块
│   ├── models/                  # 碳排放子模型
│   └── utils/                   # 工具函数
├── notebooks/                   # Jupyter分析笔记本
├── results/                     # 模型结果与图表
└── tests/                       # 单元测试
```

---

## 🔬 研究背景

AAO工艺是目前应用最广泛的生物脱氮除磷污水处理工艺之一。其碳排放来源包括：

- **直接排放**：处理过程中产生的 CH₄、N₂O 等温室气体
- **间接排放**：曝气能耗、药剂投加等对应的电力/化石能源消耗
- **污泥处理**：污泥厌氧消化、脱水、焚烧等环节

在实际工程中，完整的在线监测系统成本高、维护难，**轻量化数据**（仅依赖常规检测指标如COD、NH₃-N、TN、TP、SS、DO等）的碳排放模型具有重要工程实用价值。

---

## 🔗 相关链接

- GitHub仓库：[leichen1223520-glitch/OAKI-project](https://github.com/leichen1223520-glitch/OAKI-project)
- 变更日志：[CHANGELOG.md](./CHANGELOG.md)
- 研究计划：[docs/research_plan.md](./docs/research_plan.md)

---

## 📝 版本控制规范

每完成一个研究阶段，均在 `docs/phase_logs/` 下生成对应日志文件，并打上 Git Tag（如 `phase-1-complete`），确保研究过程完全可追溯。

---

*最后更新：2026-07-21*
