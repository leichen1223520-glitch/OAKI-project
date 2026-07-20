# 第五章 全厂集成碳排放模型

## 5.1 集成模型架构设计

### 5.1.1 设计目标

全厂集成碳排放模型（FPCM，Full-Plant Carbon emission Model）的架构设计目标为：

- **模块化**：各子模型相互独立，可单独调用、验证和更新；
- **灵活性**：根据可用数据级别（Level 1～4）自动切换计算策略；
- **可追溯性**：每次计算均记录输入参数、中间变量和输出结果；
- **不确定性传播**：支持蒙特卡洛采样，输出碳排放的置信区间。

### 5.1.2 模型架构层次

```
┌─────────────────────────────────────────────────┐
│               FPCM 集成框架                      │
├─────────────────────────────────────────────────┤
│  数据层：输入验证 → 缺失值处理 → 数据标准化       │
├─────────────────────────────────────────────────┤
│  计算层：                                        │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│    │ M1:CH₄   │  │ M2:N₂O   │  │ M3:曝气  │    │
│    └──────────┘  └──────────┘  └──────────┘    │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│    │ M4:其他  │  │ M5:药剂  │  │ M6:污泥  │    │
│    │  能耗    │  │  投加    │  │  处置    │    │
│    └──────────┘  └──────────┘  └──────────┘    │
├─────────────────────────────────────────────────┤
│  汇总层：Scope分类 → GWP换算 → 总量计算          │
├─────────────────────────────────────────────────┤
│  输出层：碳排放报告 + 不确定性区间 + 可视化       │
└─────────────────────────────────────────────────┘
```

### 5.1.3 数据级别自适应策略

模型根据输入数据的完整性自动选择计算精度等级：

```python
def select_calculation_level(input_data: dict) -> int:
    """
    根据可用数据自动判断计算精度级别
    Level 1: 仅流量+电耗 → 排放因子粗估（±50%）
    Level 2: ≥7项L-Core参数 → 子模型计算（±20%）
    Level 3: 完整L-Core → 全模型（±15%）
    Level 4: L-Core + L-Ext → 最高精度（±10%）
    """
    core_params = ['Q_in','COD_in','TN_in','TN_out',
                   'NH3N_in','NH3N_out','MLSS','E_total','W_sludge']
    ext_params  = ['DO_aer','T_liquid','NO3N_out','BOD5_in']
    
    core_available = sum(1 for p in core_params if p in input_data)
    ext_available  = sum(1 for p in ext_params  if p in input_data)
    
    if core_available >= 9 and ext_available >= 3:
        return 4
    elif core_available >= 9:
        return 3
    elif core_available >= 7:
        return 2
    else:
        return 1
```

---

## 5.2 子模型接口与数据流

### 5.2.1 标准化输入接口

所有子模型接受统一格式的参数字典（`ModelInput`）和参数对象（`ModelParams`）：

```python
@dataclass
class ModelInput:
    """标准化模型输入"""
    # 基础水量
    Q_in: float              # m³/d，日均进水量
    
    # 进水水质（mg/L）
    COD_in: float
    TN_in: float
    NH3N_in: float
    TP_in: float = None
    SS_in: float = None
    BOD5_in: float = None    # 可选
    
    # 出水水质（mg/L）
    TN_out: float = None
    NH3N_out: float = None
    TP_out: float = None
    COD_out: float = None
    
    # 运行参数
    MLSS: float = 4000       # mg/L
    DO_aer: float = 2.0      # mg/L，可选
    T_liquid: float = 20.0   # °C，可选
    
    # 能耗与污泥（月度数据）
    E_total_monthly: float = None   # kWh/月
    W_sludge_monthly: float = None  # tDS/月
    
    # 药剂（月度，可选）
    PAC_monthly: float = 0   # kg/月
    carbon_monthly: float = 0 # kg/月
    
    # 统计周期
    days_in_period: int = 365    # 计算周期天数
    
    # 污泥处置方式
    sludge_disposal: str = "landfill"  # landfill/compost/digestion/incineration


@dataclass 
class ModelParams:
    """可率定模型参数"""
    # CH₄子模型
    MCF: float = 0.03
    B0: float = 0.6
    f_BOD_COD: float = 0.50
    f_sludge_organic: float = 0.25
    
    # N₂O子模型
    EF_nit: float = 0.0032
    EF_denit: float = 0.0016
    K_DO_N2O: float = 1.5
    CN_critical: float = 8.0
    
    # 能耗子模型
    k_aer: float = 0.015
    k_BOD: float = 0.0004
    r_aer_fraction: float = 0.58   # 曝气占总电耗比例
    
    # 污泥子模型
    Y_obs: float = 0.40
    
    # 电网排放因子
    EF_grid: float = 0.5839       # kgCO₂/kWh（2022中国平均）
```

### 5.2.2 标准化输出接口

```python
@dataclass
class ModelOutput:
    """集成模型标准化输出"""
    # Scope 1 直接排放
    E_CH4_kg: float          # kgCH₄/计算周期
    E_N2O_kg: float          # kgN₂O/计算周期
    E_Scope1_CO2eq: float    # kgCO₂eq
    
    # Scope 2 间接排放
    E_aer_kWh: float         # 曝气电耗 kWh
    E_total_kWh: float       # 总电耗 kWh
    E_Scope2_CO2eq: float    # kgCO₂eq
    
    # Scope 3 上下游排放
    E_chem_CO2eq: float      # 药剂 kgCO₂eq
    E_sludge_CO2eq: float    # 污泥 kgCO₂eq
    E_Scope3_CO2eq: float    # kgCO₂eq
    
    # 合计
    E_total_CO2eq: float     # kgCO₂eq
    E_unit_kgCO2_m3: float   # 单位碳排放强度 kgCO₂eq/m³
    
    # 元数据
    calculation_level: int
    uncertainty_pct: float   # 预估不确定性（%）
    warnings: list           # 数据质量警告
```

---

## 5.3 模型参数率定方法

### 5.3.1 贝叶斯参数率定框架

鉴于模型参数的不确定性较大，本研究采用**贝叶斯推断**方法进行参数率定，将先验知识（文献范围）与有限的实测数据（如企业历史碳排放数据）相结合，获得参数的后验分布。

**贝叶斯更新公式：**

$$p(\boldsymbol{\theta} | \mathbf{y}) \propto p(\mathbf{y} | \boldsymbol{\theta}) \times p(\boldsymbol{\theta})$$

其中：
- $\boldsymbol{\theta}$：待率定参数向量（如 MCF, EF_nit, EF_denit 等）
- $\mathbf{y}$：观测数据（已知年度总排放量或单项排放实测值）
- $p(\boldsymbol{\theta})$：参数先验分布（由文献范围确定）
- $p(\mathbf{y}|\boldsymbol{\theta})$：似然函数（观测值与模型输出的偏差）

### 5.3.2 似然函数设计

假设模型计算值与实测值之间的误差服从对数正态分布（适合碳排放等正值变量）：

$$\log(y_i) \sim \mathcal{N}(\log(\hat{y}_i(\boldsymbol{\theta})), \sigma^2)$$

其中 $\sigma$ 为误差标准差，视数据质量而定（月度数据取 $\sigma \approx 0.15$）。

### 5.3.3 MCMC采样

使用Markov Chain Monte Carlo（MCMC）方法从后验分布采样，具体采用No-U-Turn Sampler（NUTS）算法（通过PyMC库实现）：

```python
import pymc as pm
import numpy as np

def calibrate_params(observed_emissions: np.ndarray, 
                     model_inputs: list) -> dict:
    """
    贝叶斯参数率定
    observed_emissions: 观测到的月度碳排放（kgCO₂eq）
    model_inputs: 对应月份的ModelInput对象列表
    """
    with pm.Model() as carbon_model:
        # 先验分布
        MCF = pm.Beta("MCF", alpha=2, beta=40)
        EF_nit = pm.LogNormal("EF_nit", mu=np.log(0.0032), sigma=0.6)
        EF_denit = pm.LogNormal("EF_denit", mu=np.log(0.0016), sigma=0.6)
        EF_grid = pm.Normal("EF_grid", mu=0.5839, sigma=0.05)
        
        # 模型预测
        predicted = []
        for inp in model_inputs:
            # 调用集成模型
            pred = run_fpcm(inp, ModelParams(MCF=MCF, EF_nit=EF_nit,
                                             EF_denit=EF_denit, EF_grid=EF_grid))
            predicted.append(pred.E_total_CO2eq)
        
        sigma = pm.HalfNormal("sigma", sigma=0.2)
        
        # 似然
        pm.Normal("obs", mu=pm.math.log(pm.math.stack(predicted)),
                  sigma=sigma, observed=np.log(observed_emissions))
        
        # MCMC采样
        trace = pm.sample(2000, tune=1000, cores=4, progressbar=True)
    
    return trace
```

### 5.3.4 参数率定数据需求

| 数据类型 | 最低需求 | 推荐数量 | 说明 |
|---------|---------|---------|------|
| 月度总碳排放 | 6个月 | 24个月 | 用于整体率定 |
| N₂O实测通量 | — | 3次以上 | 若有，显著提升N₂O参数精度 |
| CH₄实测通量 | — | 2次以上 | 若有，率定MCF |
| 单元电耗 | — | 6个月 | 若有，校验曝气模型 |

---

## 5.4 模型验证方案

### 5.4.1 验证策略

本研究采用**留一交叉验证（Leave-One-Out Cross-Validation, LOO-CV）**策略：

1. 将历史数据按月划分，依次留出一个月数据作为验证集，其余数据用于率定；
2. 计算每次验证的预测误差；
3. 汇总所有验证误差，计算LOO-CV误差统计量。

**时间序列分割**（针对月度数据）：
- 前18个月：训练集（参数率定）
- 后6个月：独立测试集（模型验证）

### 5.4.2 验证指标

| 指标 | 公式 | 说明 | 可接受标准 |
|------|------|------|----------|
| 相对误差（RE） | $(E_{pred}-E_{obs})/E_{obs} \times 100\%$ | 整体偏差 | $|RE| \leq 15\%$ |
| 均方根误差（RMSE） | $\sqrt{\frac{1}{n}\sum(E_{pred,i}-E_{obs,i})^2}$ | 预测精度 | — |
| Nash-Sutcliffe效率系数（NSE） | $1 - \sum(E_{obs}-E_{pred})^2/\sum(E_{obs}-\bar{E}_{obs})^2$ | 模型解释力 | $NSE \geq 0.7$ |
| 皮尔逊相关系数（r） | — | 趋势一致性 | $r \geq 0.85$ |
| 95%置信区间覆盖率 | 观测值落入CI的比例 | 不确定性合理性 | $\geq 90\%$ |

---

## 5.5 模型评估指标

### 5.5.1 精度评估矩阵

| 数据级别 | 全厂总量RE | N₂O RE | CH₄ RE | Scope2 RE |
|---------|---------|--------|--------|----------|
| Level 1 | ±50% | — | — | ±20% |
| Level 2 | ±20% | ±40% | ±30% | ±12% |
| Level 3 | ±15% | ±30% | ±22% | ±8% |
| Level 4 | ±10% | ±20% | ±15% | ±6% |

### 5.5.2 碳排放强度指标

除总量外，模型同步输出以下强度指标，便于横向对比：

| 指标 | 单位 | 说明 |
|------|------|------|
| 单位水量碳排放 | kgCO₂eq/m³ | 与处理规模无关 |
| 单位去除COD碳排放 | kgCO₂eq/kgCOD_removed | 反映处理效率 |
| 单位去除TN碳排放 | kgCO₂eq/kgTN_removed | 脱氮相关碳排放 |
| 单位电耗碳强度 | kgCO₂eq/kWh | 电力间接排放强度 |

---

## 5.6 本章小结

本章完成了全厂集成碳排放模型（FPCM）的架构设计：

1. **四层架构**：数据层→计算层→汇总层→输出层，确保模块清晰、可维护；

2. **数据自适应**：根据输入数据完整性自动选择Level 1～4计算精度，保证在任何数据条件下都能给出有用的估算结果；

3. **标准化接口**：`ModelInput`、`ModelParams`和`ModelOutput`三个数据类定义了统一的接口规范；

4. **贝叶斯率定**：采用PyMC实现MCMC参数率定，充分利用先验知识，支持有限数据条件下的参数估计；

5. **严格验证**：采用LOO-CV策略和多项评估指标（NSE ≥ 0.7、r ≥ 0.85）确保模型可靠性。

---

*章节版本：v1.0 | 更新日期：2026-07-21*
