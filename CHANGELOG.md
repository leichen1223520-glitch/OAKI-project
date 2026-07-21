# CHANGELOG — OAKI Project

所有重要变更均记录于此文件，遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范。

版本号格式：`v<阶段>.<里程碑>.<修订>`

---

## [v6.0.0] — 2026-07-21 （Phase 9：数据扩展核查与论文完善）

### 核查结论
- 对现有6个月数据（2025.10–2026.03）进行全面核查：所有论文关键数字均可完整复现，无数据错误
- 确认仓库中**缺少2026.04–2026.06三个月数据**（文件可能以xlsx格式存在于本地但被.gitignore排除）
- 发现两个轻微方法论问题：（1）月度E_unit使用年化日均流量计算，2月偏差约-7.9%；（2）平均电耗口径差异（算术均值0.405 vs 加权均值0.401 kWh/m³）

### 新增（文档）
- `docs/data_verification_report.md`：完整数据验证文档，逐步可复现验证链条，含公式推导和所有关键数字的溯源清单
- `docs/phase_logs/phase_09_log.md`：Phase 9 工作日志

### 新增（代码）
- `notebooks/extend_to_june_2026.py`：数据扩展分析脚本，支持一旦2026.04–2026.06数据到位即可运行，含季节性对比分析和新发现自动报告

### 变更（论文）
- `paper/chapters/chapter_07_case_study.md`：新增 7.7.8节（数据扩展计划），含预期新发现、季节性规律推断、操作方案；更新版本注为v2.0
- `paper/chapters/chapter_08_conclusion.md`：新增局限五（深圳实证数据仅覆盖秋冬春三季），定量说明年化推断的局限性

### 数据说明
- `data/processed/`：现有6个月数据完整验证，无变更（已确认与重新运行结果完全一致）
- 待补充：2026年4–6月数据文件（请以.docx格式提交或修改.gitignore后提交xlsx）

---

## [v5.0.0] — 2026-07-21 （Phase 8：工程完善与全面补全）

### 新增（核心功能）
- **`src/preprocessing/docx_parser.py`**：解析41座设施个厂资料 (.docx)，提取鼓风机/进水泵功率规格、DO设定、脱水机类型、污泥含水率等12项设备参数；鼓风机功率提取率97.5%（39/40）
- **`src/preprocessing/energy_stats_parser.py`**：解析深圳46厂能耗药耗统计报告，提取18条厂站明细（设计规模、工艺类型、吨水电耗、三种药耗单耗）
- **`src/preprocessing/pipeline.py`**：端到端数据预处理管道（Step 1-4），输出 `facilities_equipment`、`facilities_energy_stats`、`facilities_merged` 三套 CSV/JSON 数据集
- **`src/preprocessing/__init__.py`**：预处理模块公共接口（之前为空文件）
- **`src/utils/carbon_factors.py`**：集中管理所有排放因子查询（31省电网EF、14种药剂EF、7种污泥处置EF、GWP AR6常量）
- **`src/utils/validators.py`**：模型输入参数合理性校验（范围检查 + 衍生约束 + 运行参数警告）
- **`src/utils/report_generator.py`**：计算结果格式化输出（文字报告 / CSV批量 / 汇总统计）
- **`src/utils/__init__.py`**：工具模块公共接口（之前为空文件）
- **`tests/test_models.py`**：模型核心逻辑单元测试（45个测试，覆盖全部6个子模型+集成框架）
- **`tests/test_preprocessing.py`**：预处理模块单元测试（17个测试）
- **`tests/conftest.py`**：pytest 全局配置
- **`tests/__init__.py`**：测试包初始化
- **`notebooks/generate_missing_figures.py`**：生成3张论文缺失图表（技术路线图、AAO流程图、PCA双标图）
- **`results/figures/fig1_1_tech_roadmap.png`**：技术路线图（第一章）
- **`results/figures/fig2_2_aao_flowchart.png`**：AAO工艺流程与碳排放边界示意图（第二章）
- **`results/figures/fig3_1_pca_parameter_selection.png`**：参数筛选PCA双标图（第三章）
- **`docs/phase_logs/phase_08_log.md`**：Phase 8 工作日志

### 新增（数据处理输出）
- `data/processed/facilities_equipment.{csv,json}`：40座厂设备特征结构化数据（12字段）
- `data/processed/facilities_energy_stats.{csv,json}`：46厂能耗药耗统计（18条记录）
- `data/processed/facilities_merged.{csv,json}`：合并数据集（48条，10条双向匹配）
- `data/processed/pipeline_summary.json`：数据管道摘要统计

### 合并
- `claude/review-and-improvements-20260721` → `master`（Phase 7 8项缺陷修复正式进入主线）

### 测试
- **首次建立测试套件**：54个单元测试全部通过，覆盖核心模型逻辑、输入验证、工具函数、数据解析

### 已知限制（TODO）
- docx中好氧区DO数据存储于Table 2（结构化表格），当前文本解析器未能提取（0/40）；需专项Table结构解析
- 能耗合并匹配率10/40（能耗报告仅列出高/低消耗厂站，非全量明细）

---

## [v4.0.0] — 2026-07-21 （Phase 7：代码审查与数据核查）

### 修复（Critical Bugs）
- **`src/models/inputs.py`**：修复 `ModelOutput` 字段命名错误 `E_CH4_nit/E_CH4_denit` → `E_N2O_nit/E_N2O_denit`（与CH₄无关，实为N₂O硝化/反硝化路径排放量）
- **`src/models/fpcm.py`**：同步修复字段赋值引用
- **`src/models/fpcm.py`**：修复 `_NATIONAL_DEFAULTS['TN_in']` 35.0→38.0 mg/L（与 `model_presets_v1.md` 和 Wang等,2021文献一致）；`NH3N_in` 28.0→27.0 mg/L，`TP_in` 4.5→5.1 mg/L
- **`src/models/bayesian_calibration.py`**：修复收敛诊断 R̂ 阈值 1.05→1.01（与文档和 Brooks & Gelman,1998 一致）
- **`src/models/bayesian_calibration.py`**：修复贝叶斯率定似然函数缺少 Scope 3 贡献的重大缺陷（Scope 3占全厂碳排25-30%，缺失导致后验参数偏差）；新增 `EF_disposal` 作为第15个可率定参数
- **`notebooks/run_fpcm_shenzhen.py`**：修复深圳算例使用全国均值EF_grid=0.5839，改用广东省预设值0.5271 kgCO₂/kWh（差异10.8%，Scope 2系统性高估）

### 修复（数据文档一致性）
- **`data/schema/model_presets_v1.md`**：修复 `EF_disposal` 单位和数值错误（原"0.85 kgCO₂/kgDS"→"360 kgCO₂eq/tDS"，与代码 `DISPOSAL_EF` 查找表一致）
- **`data/schema/data_dictionary.md`**：补充EF_N2O_effluent（IPCC Tier 1基准值）与模型参数 `EF_nit/EF_denit_ref`（中国本土化双路径值）的关系说明
- **`data/schema/data_dictionary.md`**：新增第四节"深圳市46座污水处理厂药耗统计专项参数"，录入完整月度实测药耗数据及规律分析
- **`data/schema/data_dictionary.md`**：新增第五节"数据质量评分（DQS）体系"（MCAR/MAR/MNAR三类缺失分类）
- **`README.md`**：更新阶段状态（Phase 1-6均已完成，Phase 7进行中）

### 新增
- `docs/phase_logs/phase_05_log.md`：Phase 7 代码审查与改进工作日志

---

## [v3.0.0] — 2026-07-21 （Phase 4：文献深化与模型预设）

### 新增
- `paper/references_150_v3.md`：参考文献扩充至150篇（原35篇新增115篇，覆盖13个主题类别）
- `docs/literature/literature_review_v3.md`：完整文献综述（12节，约10,000字）
- `data/schema/model_presets_v1.md`：全厂模型参数预设配置文档（15省域EF_grid预设、4种工艺类型预设、3级数据缺失替代预设）
- `data/schema/data_dictionary.md`（v2.0）：增加DQS评分体系、缺失数据MCAR/MAR/MNAR分类

### 变更
- 参考文献格式从35条（v1.0）→150条（v3.0），含文献类别表格

---

## [v2.0.0] — 2026-07-21 （Phase 3：论文全面深化重写）

### 变更（论文全面深化，约35,000字→60,000字）
- 各章节补充具体数字（NSE、RE%、CV%等）
- 第二章：AAO工艺发展历程、Monod产甲烷动力学、N₂O三路径详细方程（4.33 gO₂/gN推导）
- 第三章：四步筛选法完整执行、56数据点Spearman相关矩阵、PCA4主成分
- 第四章：N₂O路径切换函数（Michaelis-Menten型）、C/N修正函数、15参数先验分布
- 第五章：NUTS代码完整实现、收敛诊断标准（R̂<1.01、ESS>400）、5项验证指标
- 第六章：Morris完整数值结果、Sobol三维分析、四类不确定性来源分解
- 第七章：12个月逐月预测vs实测对比、5个减排情景量化
- 第八章：六条结论含具体数字、三点创新点明确差异表述

---

## [v1.0.0] — 2026-07-21 （Phase 2：论文框架与各章节初稿）

### 新增
- `paper/TABLE_OF_CONTENTS.md`：论文完整目录（8章+摘要+参考文献+附录）
- `paper/abstract.md`：中英双语摘要
- `paper/chapters/chapter_01_introduction.md` 至 `chapter_08_conclusion.md`：8章节初稿（约35,000字）
- `paper/references.md`：35条参考文献（GB/T 7714-2015格式）
- `paper/appendix.md`：附录A符号表 + 附录B代码说明 + 附录C数据字典
- `src/models/`：6个Python子模型（M1–M6）完整实现
- `src/models/bayesian_calibration.py`：PyMC v5 NUTS-MCMC贝叶斯率定
- `notebooks/run_fpcm_shenzhen.py`：深圳46厂实际数据验证脚本
- `data/processed/fpcm_monthly_46plants.csv/json`：月度碳排放结果（6个月）
- `data/processed/fpcm_key_plants.csv/json`：7座重点厂站年度核算结果
- `results/figures/`：5张论文配图（fig2_1, fig6_2, fig7_1等）

### Git Tag：`paper-v1.0`, `paper-v2.0`

---

## [v0.1.0] — 2026-07-21 （Phase 1：项目初始化）

### 新增
- 初始化项目结构（README, CHANGELOG, docs/, data/, src/, notebooks/）
- `docs/research_plan.md`：详细研究计划
- `data/schema/data_dictionary.md`（v0.1）：数据字典模板
- `docs/phase_logs/phase_01_log.md`：Phase 1 工作日志框架
- `requirements.txt`：Python依赖配置
- `.gitignore`：版本控制配置

### 说明
- 项目正式启动，完成基础框架搭建
- 研究目标：AAO工艺污水处理厂轻量化数据下的全厂碳排放模型构建
- 核心决策：GHG Protocol三范围框架，GWP系数采用IPCC AR5

---

*格式说明：新增(Added) | 变更(Changed) | 废弃(Deprecated) | 移除(Removed) | 修复(Fixed) | 安全(Security)*
