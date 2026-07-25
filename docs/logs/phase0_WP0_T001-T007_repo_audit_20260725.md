# 阶段日志：WP0 / 任务T001-T007（阶段0：项目接管与仓库审计）

**任务编号**：T001, T002, T003, T004, T005, T006, T007  
**任务名称**：仓库审计与项目治理文件建立（阶段0）  
**状态**：COMPLETED（T001/T003/T004/T005/T006/T007）；PARTIAL（T002）  
**日期**：2026-07-25  

---

## 基本信息

**Git提交号**：待提交（本日志完成后提交）  
**数据版本**：无（本阶段仅文档工作）  
**运行环境**：claude代理环境  

---

## 输入

**现有仓库状态**：
- 主分支最新提交：`2f67fa2 feat(phase9): 数据扩展至2026年6月`
- 现有论文草稿：FPCM框架，8章，v3.0
- 现有代码：Python FPCM M1-M6子模型
- 现有数据：深圳46厂月度数据（2025.10-2026.06）

---

## 目标

建立满足OAKI框架要求的仓库目录结构，并完成任务书完备性审查。

---

## 执行内容

1. **仓库审计**：检查现有目录结构、代码、数据、文档
2. **发现关键问题**：
   - 现有FPCM框架（8章）与新OAKI框架（9章）存在根本性差异
   - BSM2G未安装，WP2（13个任务）全部BLOCKED
   - FULL_PAPER.md中"2案例厂2022-2023年验证"数据来源不明
   - 无PyTorch/多任务学习依赖
3. **建立新目录结构**：增加src/simulation/, src/asm/, src/calibration/, src/carbon/, src/evaluation/, docs/reviews/, docs/design/等
4. **创建项目治理文档**：
   - `docs/reviews/taskbook_audit.md`：任务书完备性审查报告
   - `docs/design/research_design_v2.md`：博士论文研究设计V2.0
   - `docs/design/thesis_outline_v2.md`：论文大纲V2.0
   - `docs/design/task_mapping.csv`：修订后94项任务清单
   - `docs/design/claim_evidence_matrix.csv`：研究问题-方法-证据映射矩阵
   - `data/schema/data_dictionary.csv`：数据字典V1.0
   - `results/manifests/results_manifest.csv`：结果清单模板
   - `docs/logs/template.md`：日志模板
   - `DATA_POLICY.md`：数据保密策略
   - `environment.yml`：更新环境文件（新增多任务学习依赖）
   - `requirements.txt`：更新依赖
   - `README.md`：完全重写，采用OAKI框架

---

## 验收标准

| 标准 | 预设 | 实际 | 通过 |
|------|------|------|------|
| 目录结构满足OAKI框架 | 是 | 是 | ✅ |
| 任务书审查报告形成 | 是 | 是 | ✅ |
| 研究设计V2.0形成 | 是 | 是 | ✅ |
| 所有94项任务有V2.0修订说明 | 是 | 是 | ✅ |
| 阻塞项明确标注 | 是 | 是 | ✅ |
| 数据字典包含BSM2G和46厂变量 | 是 | 是 | ✅ |

---

## 已知问题

1. **P0-001**：FULL_PAPER.md中的验证结论（8.3%/12.1%误差）无对应数据文件，需用户澄清或删除
2. **P0-002**：BSM2G安装等待用户确认（MATLAB版本、许可证）
3. **P0-003**：T002（GitHub Issues建立）需要仓库协作权限或用户操作

---

## 结论边界

本阶段工作均为文档和项目治理，无数据或实验，无结论边界限制。

---

## 下一步

优先级P0（立即执行）：
- T026：整理46厂月度数据
- T083：开始绪论初稿写作
- T009：锁定论文题目与中心问题（已在V2.0中确认）

等待用户确认：
- BSM2G获取方式（T016前提条件）
- 单厂高频数据变量清单（T033前提条件）
- 两座代表性监测厂的意向（T032前提条件）
- 现场GHG监测计划（T061前提条件）
