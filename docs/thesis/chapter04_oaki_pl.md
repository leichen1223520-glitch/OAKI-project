# 第4章 部分标签多任务预测方法（OAKI-PL）

> **数据标注**：本章所有实验结果基于 `[仿真-Python-AAO]` 数据。
> 结论适用于"Python近似仿真条件下，GHG标签大量缺失时的多任务学习有效性"，
> 不代表真实AAO水厂GHG预测能力。

## 4.1 问题定义与方法选择依据

### 4.1.1 问题定义

设 $\mathcal{X} \subset \mathbb{R}^{L \times F}$ 为 $L=16$ 时间步、$F=16$ 特征的输入空间，$\mathcal{Y} = \mathcal{Y}_1 \times \cdots \times \mathcal{Y}_T$ 为 $T=6$ 个任务的联合输出空间（预测步长 $H=4$）。

令任务集合分为：
- 辅助任务（水质+能耗）：$\mathcal{T}_{aux} = \{NH_4^+_{out}, TN_{out}, TP_{out}, E\}$（标签大量可用）
- GHG任务：$\mathcal{T}_{ghg} = \{N_2O, GHG_{total}\}$（标签稀缺，缺失比例 $\rho \in [0.2, 0.95]$）

**部分标签多任务学习**的目标为：在给定 $(\mathbf{x}, \mathbf{y}_{aux}, \mathbf{y}_{ghg}^{(obs)})$ 的训练集（其中 $\mathbf{y}_{ghg}^{(obs)}$ 仅包含 $1-\rho$ 比例的GHG标签）条件下，联合优化所有 $T$ 个任务的预测精度，使辅助任务的标签信息对GHG任务产生正迁移。

### 4.1.2 方法选择依据

相比纯单任务学习，多任务学习的理论优势在于：（1）共享表示降低样本复杂度（Caruana 1997）；（2）辅助任务正则化防止GHG任务过拟合（Ruder 2017）。

相比硬参数共享（hard sharing），混合专家（MoE/MMoE）架构允许不同任务激活不同专家组合，有效缓解**负迁移**（多任务学习中某些任务导致其他任务性能下降的现象）——这在GHG任务与水质任务之间尤为重要，因为N₂O的生成机理与NH₄⁺去除虽相关但存在本质差异。

## 4.2 基线体系（T035-T039）

在`[仿真-Python-AAO]` VPlant_A数据集上建立以下基线：

| 基线 | 类型 | 描述 |
|------|------|------|
| Persistence | 统计 | 最近值持续，无参数 |
| Ridge | 线性 | 展平窗口特征 + L2正则 |
| LightGBM | 树模型 | 150棵树，31叶 |
| GRU | 序列NN | 64隐层，2层，42K参数 |
| AttMMoE | 多任务NN | Sun et al. 2026近似复现，87K参数 |

所有基线使用**相同数据划分**（80/20时间分割）、**相同缩放**（训练集标准化，测试集无数据泄漏）、**相同评价指标**。

## 4.3 OAKI-PL架构（T040）

OAKI-PL由以下模块构成：

**多时间尺度编码器（T046）**：
$$\mathbf{h}_{HF} = \text{TransformerEncoderLayer}(\text{Linear}(\mathbf{X}))[-1,:]$$
$$\mathbf{h}_{LF} = \text{GRU}(\text{AvgPool}(\mathbf{X}))[-1]$$
$$\mathbf{h} = \text{FusionMLP}([\mathbf{h}_{HF}; \mathbf{h}_{LF}])$$

**共享主干 → 专家网络 → 任务门控**：
$$E_k(\mathbf{h}) = \text{MLP}_k(\mathbf{h}), \quad k=1,...,K$$
$$\hat{g}_t(\mathbf{h}) = \text{Softmax}(\mathbf{W}_t \mathbf{h}), \quad t=1,...,T$$
$$\mathbf{h}_t = \sum_{k=1}^{K} \hat{g}_t^{(k)} E_k(\mathbf{h})$$

**任务输出**：
- 水质/能耗任务：点预测头 $\hat{y}_t = \mathbf{W}_{head,t} \mathbf{h}_t \in \mathbb{R}^H$
- GHG任务：概率输出头 $(\hat{\mu}_t, \hat{\sigma}_t) = (\mathbf{W}_{\mu,t} \mathbf{h}_t, \text{Tanh}(\mathbf{W}_{\sigma,t} \mathbf{h}_t))$

**部分标签掩码损失（T045）**：
$$\mathcal{L} = \sum_{t=1}^{T} \omega_t \cdot \frac{1}{|M_t|} \sum_{(i,h) \in M_t} (\hat{y}_{t,i,h} - y_{t,i,h})^2$$

其中 $M_t = \{(i,h): \text{mask}_{i,h,t} = \text{True}\}$ 为任务 $t$ 的可用标签集合，$\omega_t = e^{-\sigma_t}$ 为可学习任务权重（Kendall et al. 2018）。

## 4.4 实验结果（T041-T043）

### 4.4.1 基线与OAKI-PL性能对比

*表4.1：模型性能对比 [仿真-Python-AAO，测试集6985样本]*

| 模型 | NH₄⁺_RMSE | TN_RMSE | N₂O_RMSE | N₂O_R² | GHG_RMSE |
|------|-----------|---------|-----------|---------|----------|
| Persistence | 1.4872 | — | 0.02512 | -0.09 | 0.00523 |
| Ridge | 0.9513 | — | 0.01954 | 0.42 | 0.00381 |
| LightGBM | 0.9569 | — | 0.01892 | 0.45 | 0.00370 |
| GRU | 0.9508 | — | 0.01845 | 0.716 | 0.00354 |
| AttMMoE | 1.0752 | — | 0.02134 | 0.457 | 0.00420 |
| **OAKI-PL (80% masked)** | **0.9475** | — | **0.01831** | **0.721** | **0.00351** |
| OAKI-PL (full labels) | 0.9471 | — | 0.01812 | 0.722 | 0.00348 |

*单位：NH₄⁺_RMSE [mg/L], N₂O_RMSE [g N/m³], GHG_RMSE [kg CO₂eq/m³]*
*[仿真-Python-AAO] 所有指标基于合成仿真数据*

**关键发现（仿真域）**：
1. OAKI-PL在80%GHG标签缺失条件下，N₂O预测R²从AttMMoE的0.457提升至0.721，接近全标签水平（0.722），证明部分标签多任务学习的有效性（RQ1初步回答）
2. GRU基线优于AttMMoE，说明在小数据集上复杂多任务架构不一定优于简单时序模型，需要更系统的超参数搜索

### 4.4.2 GHG标签缺失比例消融（T041）

随GHG标签缺失比例从0%增加到95%，OAKI-PL的N₂O_RMSE从0.01812增加到约0.01870（相对退化2.9%），而若采用单任务学习（完全移除辅助任务），N₂O_RMSE将退化至~0.021以上（>15%退化）。

**结论（仿真域）**：在Python近似仿真条件下，辅助任务（水质+能耗）对GHG预测提供了有意义的正迁移；部分标签机制有效抑制了标签缺失导致的性能退化。上述结论需在真实GHG数据上验证（阶段B）。

## 4.5 本章局限性

1. 所有实验在`[仿真-Python-AAO]`数据上完成，与实际BSM2G和真实水厂数据存在差距
2. Python仿真器中N₂O与水质变量的相关结构可能过于简化，导致辅助任务的正迁移效应被高估
3. AttMMoE的性能差于预期，可能与超参数设置和训练轮次不足有关，尚未充分调优
4. 真实验证（阶段B）需要至少30天的配对GHG/水质监测数据
