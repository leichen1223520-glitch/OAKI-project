# 摘要

## 中文摘要

污水处理行业是城市碳排放的重要来源之一，推动其低碳转型对实现"双碳"目标具有重要意义。AAO（厌氧-缺氧-好氧，Anaerobic-Anoxic-Oxic）工艺是目前国内应用最广泛的生物脱氮除磷污水处理工艺，其碳排放来源涵盖生物处理过程中产生的CH₄与N₂O等直接温室气体、曝气与输水能耗对应的间接碳排放，以及药剂投加和污泥处置的上下游排放。然而，现有全厂碳排放模型大多依赖完整的在线监测数据，在数据基础薄弱的中小型污水处理厂中难以推广应用。

本研究提出"轻量化数据"概念，即仅依赖污水处理厂常规检测指标（进出水COD、TN、NH₃-N、TP、SS、DO、MLSS及月度电耗、污泥产量等）构建全厂碳排放模型，以降低碳排放核算门槛，扩大适用范围。

在碳排放核算边界方面，本研究采用GHG Protocol三范围框架，全球增温潜势（GWP）系数参照IPCC第五次评估报告（AR5）100年时间框架取值。在模型构建方面，分别针对厌氧池/管网CH₄排放、好氧/缺氧池N₂O排放、曝气及泵类能耗间接排放、药剂投加及污泥处理上下游排放建立机理-经验混合子模型，再通过标准化接口集成为全厂碳排放计算框架。通过贝叶斯参数率定和蒙特卡洛不确定性分析对模型进行验证与评估，并采用Sobol全局灵敏度方法识别影响模型精度的关键参数。

结果表明：（1）在轻量化数据条件下，集成模型可实现全厂年度碳排放总量估算，与全量监测数据模型的偏差控制在±15%以内；（2）N₂O是AAO工艺最大的直接碳排放源，占全厂Scope 1排放的60%以上；（3）曝气能耗是间接碳排放的主体，占Scope 2排放的65～75%；（4）出水TN浓度和DO控制水平对N₂O排放贡献最为敏感，是优先监测的关键参数。

本研究为数据条件有限的污水处理厂提供了一套可操作的全厂碳排放核算工具，并以开源Python工具包形式发布，对推动污水处理行业碳排放精细化管理具有重要实践价值。

**关键词**：AAO工艺；碳排放模型；轻量化数据；N₂O；温室气体核算；污水处理厂

---

## Abstract

Wastewater treatment is a notable contributor to urban carbon emissions, and its low-carbon transition is critical for achieving China's "dual carbon" goals. The Anaerobic-Anoxic-Oxic (AAO) process is the most widely applied biological nitrogen and phosphorus removal technology in China, with carbon emissions arising from direct greenhouse gases (CH₄ and N₂O) produced during biological treatment, indirect emissions from aeration and pumping energy consumption, and upstream/downstream emissions from chemical dosing and sludge disposal. However, existing full-plant carbon emission models predominantly rely on comprehensive online monitoring data, limiting their applicability in small and medium-sized wastewater treatment plants (WWTPs) with weak data infrastructure.

This study introduces the concept of "lightweight data"—constructing a full-plant carbon emission model using only routine monitoring parameters (influent/effluent COD, TN, NH₃-N, TP, SS, DO, MLSS, monthly electricity consumption, and sludge production)—to lower the threshold for carbon accounting and broaden applicability.

The carbon accounting boundary follows the GHG Protocol three-scope framework, with global warming potential (GWP) factors sourced from the IPCC Fifth Assessment Report (AR5) using a 100-year time horizon. Mechanistic-empirical hybrid sub-models are developed for CH₄ emissions from anaerobic tanks/sewers, N₂O emissions from aerobic/anoxic tanks, indirect energy-related emissions from aeration and pumping, and upstream/downstream emissions from chemical dosing and sludge treatment. These sub-models are integrated into a full-plant carbon emission framework through standardized interfaces. Bayesian parameter calibration and Monte Carlo uncertainty analysis are applied for model validation and assessment, while Sobol global sensitivity analysis identifies key parameters governing model accuracy.

Results indicate that: (1) under lightweight data conditions, the integrated model can estimate annual full-plant carbon emissions with a deviation within ±15% compared to models using complete monitoring data; (2) N₂O is the largest direct emission source in AAO processes, accounting for over 60% of Scope 1 emissions; (3) aeration energy consumption dominates indirect emissions, comprising 65–75% of Scope 2 emissions; (4) effluent TN concentration and dissolved oxygen control level are the most sensitive parameters for N₂O emissions and should be prioritized in monitoring.

This study provides a practical full-plant carbon accounting tool for WWTPs with limited data infrastructure, released as an open-source Python package, offering significant value for advancing refined carbon emission management in the wastewater treatment sector.

**Keywords**: AAO process; carbon emission model; lightweight data; N₂O; greenhouse gas accounting; wastewater treatment plant
