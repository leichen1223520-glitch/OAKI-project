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
| Phase 1 | 项目初始化与框架搭建 | 仓库结构、研究计划、版本控制规范 | ✅ 完成 |
| Phase 2 | 论文框架与各章节初稿（v1.0）| 8章节初稿，35条参考文献，~35,000字 | ✅ 完成 |
| Phase 3 | 论文全面深化重写（v2.0）| 机理推导、具体数字、双语摘要，~60,000字 | ✅ 完成 |
| Phase 4 | 文献深化 + 模型预设（v3.0）| 150篇文献、文献综述、省域EF预设 | ✅ 完成 |
| Phase 5 | Python代码实现 | FPCM v3.0全套子模型（M1–M6）+ 贝叶斯率定 | ✅ 完成 |
| Phase 6 | 案例数据分析与验证 | 深圳46厂实际数据运行 + 论文配图 | ✅ 完成 |
| Phase 7 | 代码审查与数据核查 | 全面审查、数据一致性修复、策略改进 | 🔄 进行中 |

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

*最后更新：2026-07-21（Phase 7 代码审查与数据核查）*
