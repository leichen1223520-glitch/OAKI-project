# 第五章 全厂集成碳排放模型（FPCM）

## 5.1 集成模型的数学形式与架构

### 5.1.1 全厂碳排放总量的分解公式

设定一个计算周期T（通常为1年=365天），全厂碳排放总量的完整数学表达式为：

$$E_{total}(T) = \underbrace{[E_{CH_4}(\boldsymbol{\theta}_{M1}, \mathbf{x}_{L}) + E_{N_2O}(\boldsymbol{\theta}_{M2}, \mathbf{x}_{L})] \times GWP}_{E_{Scope1}} + \underbrace{E_{total,kWh} \times EF_{grid}}_{E_{Scope2}} + \underbrace{E_{chem}(\mathbf{x}_{L}) + E_{sludge}(\boldsymbol{\theta}_{M6}, \mathbf{x}_{L})}_{E_{Scope3}}$$

其中：
- $\mathbf{x}_{L}$：L-Core输入数据向量（10维）或L-Ext（16维）
- $\boldsymbol{\theta}_{M1}$、$\boldsymbol{\theta}_{M2}$、$\boldsymbol{\theta}_{M6}$：各子模型的可率定参数向量（总计15维，见表4-4）
- 全部子模型均为显式代数方程（无微分方程），计算代价极低（单次运算<0.01秒，支持10,000次蒙特卡洛）

### 5.1.2 数据级别自适应的形式化定义

定义输入数据完整性评分函数L(·)：

$$L(\mathbf{x}) = \mathbb{1}_{core\_complete}(\mathbf{x}) \cdot [2 + \mathbb{1}_{ext\_partial}(\mathbf{x}) + \mathbb{1}_{ext\_full}(\mathbf{x})]$$

其中：
- Level 1：L=1（仅Q_in + E_total，其余用全国均值代替）
- Level 2：L=2（≥7项L-Core参数）
- Level 3：L=3（完整L-Core，10项全有）
- Level 4：L=4（L-Core + ≥3项L-Ext）

各级别对应的子模型精度参数自动切换（表5-1）：

**表5-1 各数据级别的子模型计算策略**

| 级别 | M1（CH₄）| M2（N₂O）| M3（曝气）| 总体不确定性（95%CI）|
|------|---------|---------|---------|-----------------|
| Level 1 | 全国均值因子 | 全国均值EF | E_total×0.576 | ±52% |
| Level 2 | IPCC Tier 2（COD输入）| 无DO修正，f_DO=1 | AOR法（部分参数）| ±22% |
| Level 3 | 完整M1（含温度修正）| 无DO修正，不确定性较大 | AOR法完整 | ±15% |
| Level 4 | 完整M1 | 含DO修正（M2-nit）| AOR法+α优化 | ±10% |

### 5.1.3 模块化计算流程

```python
class FPCM:
    """
    Full-Plant Carbon emission Model
    AAO工艺污水处理厂全厂碳排放集成模型
    """
    def __init__(self, params: ModelParams = None):
        self.params = params or ModelParams()  # 使用先验默认值
        self.M1 = CH4Model(self.params)
        self.M2 = N2OModel(self.params)
        self.M3 = AerationEnergyModel(self.params)
        self.M4 = OtherEnergyModel(self.params)
        self.M5 = ChemicalModel(self.params)
        self.M6 = SludgeDisposalModel(self.params)
    
    def run(self, inp: ModelInput, validate: bool = True) -> ModelOutput:
        # Step 0: 数据质量控制
        if validate:
            warnings = self._validate_inputs(inp)
        
        # Step 1: 确定计算级别
        level = self._determine_level(inp)
        
        # Step 2: 数据预处理（缺失值填补）
        inp = self._impute_missing(inp, level)
        
        # Step 3: 各子模型计算
        e_ch4_kg    = self.M1.calculate(inp)  # kgCH₄/年
        e_n2o_kg    = self.M2.calculate(inp)  # kgN₂O/年
        e_scope1    = e_ch4_kg * 28 + e_n2o_kg * 265
        
        e_total_kwh = inp.E_total_monthly * 12
        e_scope2    = e_total_kwh * self.params.EF_grid
        
        e_chem      = self.M5.calculate(inp)  # kgCO₂eq/年
        e_sludge    = self.M6.calculate(inp)  # kgCO₂eq/年
        e_scope3    = e_chem + e_sludge
        
        # Step 4: 汇总与不确定性估算
        e_total = e_scope1 + e_scope2 + e_scope3
        uncertainty = self._estimate_uncertainty(level)
        
        return ModelOutput(
            E_CH4_kg=e_ch4_kg,
            E_N2O_kg=e_n2o_kg,
            E_Scope1_CO2eq=e_scope1,
            E_total_kWh=e_total_kwh,
            E_Scope2_CO2eq=e_scope2,
            E_chem_CO2eq=e_chem,
            E_sludge_CO2eq=e_sludge,
            E_Scope3_CO2eq=e_scope3,
            E_total_CO2eq=e_total,
            E_unit_kgCO2_m3=e_total/(inp.Q_in*365*1000),
            calculation_level=level,
            uncertainty_pct=uncertainty,
            warnings=warnings
        )
```

---

## 5.2 贝叶斯参数率定方法

### 5.2.1 贝叶斯推断框架的必要性

传统参数率定（最小二乘法、极大似然估计）在数据充足时有效，但在本研究的轻量化数据场景中存在三个关键问题：

**问题1（过拟合）**：月度数据通常仅有12～24个观测点，而模型有15个参数，传统率定极易过拟合；  
**问题2（参数辨识性不足）**：N₂O排放因子EF_nit与路径切换函数中的f_max在有限数据下高度相关（不可分辨），传统率定无法量化这种不确定性；  
**问题3（非对称分布）**：MCF、EF_nit等参数具有严格的非负约束和重尾分布特征，正态分布假设不成立。

贝叶斯推断通过后验分布 $p(\boldsymbol{\theta}|\mathbf{y}) \propto p(\mathbf{y}|\boldsymbol{\theta}) \cdot p(\boldsymbol{\theta})$ 自然解决上述三个问题：先验 $p(\boldsymbol{\theta})$ 防止过拟合，后验协方差矩阵量化参数相关性，对数正态等非对称分布可作为先验直接使用。

### 5.2.2 似然函数的推导与正当性

**观测模型**：假设月度碳排放的观测误差（来自测量不确定性和模型结构误差）在对数空间服从正态分布：

$$\log(y_m) = \log(\hat{y}_m(\boldsymbol{\theta}, \mathbf{x}_m)) + \varepsilon_m, \quad \varepsilon_m \sim \mathcal{N}(0, \sigma^2)$$

对应的似然函数为：

$$p(\mathbf{y}|\boldsymbol{\theta}, \sigma) = \prod_{m=1}^{M} \frac{1}{y_m \sigma \sqrt{2\pi}} \exp\left(-\frac{[\log(y_m) - \log(\hat{y}_m(\boldsymbol{\theta}))]^2}{2\sigma^2}\right)$$

对数正态误差假设的正当性：  
（1）碳排放量严格为正，对数空间的正态分布自然满足非负约束；  
（2）实测研究（Flores-Alsina等，2021）表明，WWTP碳排放的月度变异系数CV约10%～25%，对应对数空间标准差σ_ln ≈ 0.10～0.22，与正态假设吻合；  
（3）对数正态误差对异常高值（如N₂O季节性峰值）的鲁棒性更强，适合污水处理这类高度异质性数据。

**残差标准差σ的超先验**：

$$\sigma \sim \text{HalfNormal}(0, 0.2)$$

这一选择允许σ在[0, ~0.5]范围内自适应，对应20%～50%的月度碳排放变异，合理覆盖数据质量差异。

### 5.2.3 NUTS-MCMC的实施细节

No-U-Turn Sampler（NUTS，Hoffman & Gelman，2014）是Hamiltonian Monte Carlo（HMC）的自适应变体，通过梯度信息高效探索高维后验空间，无需手动调整步长（与Metropolis-Hastings相比）。本研究的NUTS配置（基于PyMC v5实现）：

```python
import pymc as pm
import numpy as np

def calibrate_fpcm(monthly_observations: np.ndarray,
                   monthly_inputs: list,
                   n_samples: int = 2000,
                   n_tune: int = 1000,
                   n_chains: int = 4) -> dict:
    """
    FPCM贝叶斯参数率定
    
    Parameters
    ----------
    monthly_observations : array, shape (M,)
        M个月的实测碳排放（kgCO₂eq/月）
    monthly_inputs : list of ModelInput, length M
        对应月份的L-Core输入数据
    
    Returns
    -------
    trace : arviz.InferenceData
        后验采样结果（含诊断统计量）
    """
    with pm.Model() as model:
        # ===== 先验分布定义 =====
        # M1 参数
        MCF     = pm.LogNormal("MCF",     mu=np.log(0.028), sigma=0.60)
        B0      = pm.Normal("B0",         mu=0.60,           sigma=0.05)
        f_boc   = pm.Normal("f_boc",      mu=0.48,           sigma=0.07)
        theta_T = pm.Normal("theta_T",    mu=1.040,          sigma=0.012)
        
        # M2-nit 参数
        EF_nit  = pm.LogNormal("EF_nit",  mu=np.log(0.0035), sigma=0.65)
        DO_opt  = pm.Normal("DO_opt",     mu=2.0,            sigma=0.3)
        f_max   = pm.LogNormal("f_max",   mu=np.log(3.0),    sigma=0.40)
        
        # M2-denit 参数
        EF_denit_ref = pm.LogNormal("EF_denit_ref", mu=np.log(0.0012), sigma=0.55)
        CN_crit = pm.Normal("CN_crit",    mu=6.5,            sigma=1.5,
                             lower=3.5, upper=10.0)
        k_g     = pm.Normal("k_g",        mu=2.0,            sigma=0.6,
                             lower=0.5, upper=4.0)
        
        # 能耗/污泥参数
        EF_grid = pm.Normal("EF_grid",    mu=0.5839,         sigma=0.03)
        r_aer   = pm.Normal("r_aer",      mu=0.576,          sigma=0.062,
                             lower=0.50, upper=0.65)
        Y_obs   = pm.Beta("Y_obs",        alpha=7, beta=10)  # 均值0.41
        
        # 残差超先验
        sigma   = pm.HalfNormal("sigma",  sigma=0.2)
        
        # ===== 构建参数字典 =====
        params = ModelParams(MCF=MCF, B0=B0, f_boc=f_boc, theta_T=theta_T,
                             EF_nit=EF_nit, DO_opt=DO_opt, f_max=f_max,
                             EF_denit_ref=EF_denit_ref, CN_crit=CN_crit, k_g=k_g,
                             EF_grid=EF_grid, r_aer=r_aer, Y_obs=Y_obs)
        
        # ===== 模型预测 =====
        fpcm = FPCM(params)
        predictions = pm.math.stack([
            fpcm.run(inp, validate=False).E_total_CO2eq
            for inp in monthly_inputs
        ])
        
        # ===== 似然 =====
        pm.Normal("obs",
                  mu=pm.math.log(predictions),
                  sigma=sigma,
                  observed=np.log(monthly_observations))
        
        # ===== NUTS采样 =====
        trace = pm.sample(
            draws=n_samples,
            tune=n_tune,
            chains=n_chains,
            target_accept=0.90,  # 提高接受率，减少发散
            return_inferencedata=True
        )
    
    return trace
```

### 5.2.4 收敛性诊断标准

对NUTS采样结果执行以下诊断，均通过才认为收敛：

| 诊断统计量 | 可接受标准 | 说明 |
|---------|---------|------|
| $\hat{R}$（Gelman-Rubin统计量）| < 1.01（对所有参数）| $\hat{R}$ > 1.05表明链间不一致 |
| 有效样本量（ESS_bulk）| > 400 per chain | ESS过低表明自相关严重 |
| 发散转换数（Divergences）| < 20（占总样本0.05%）| 发散过多表明后验几何复杂 |
| Monte Carlo标准误（MCSE）| < 5% of posterior SD | 采样误差相对于后验变异度 |

---

## 5.3 模型验证方案

### 5.3.1 验证数据集划分策略

考虑到月度碳排放数据存在季节性自相关，本研究采用**时序感知的滑动窗口交叉验证（Expanding Window Cross-Validation）**替代简单的随机K折CV：

```
数据：24个月（2022年1月-2023年12月）

验证方案1（主要验证）：
├── 训练集：2022年全年（12个月）→ 参数率定
└── 测试集：2023年全年（12个月）→ 独立验证（避免数据泄露）

验证方案2（稳健性检验）：
├── 训练集：前18个月 → 率定
└── 验证：后6个月（移动3个月重叠）→ 交叉验证6次

验证方案3（最小数据量评估）：
└── 仅用6个月率定，评估短期数据的率定效果
```

### 5.3.2 性能评估指标体系

**指标1：年度相对误差（Annual RE）**

$$RE_{annual} = \frac{\sum_{m=1}^{12} \hat{y}_m - \sum_{m=1}^{12} y_m}{\sum_{m=1}^{12} y_m} \times 100\%$$

**指标2：月度Nash-Sutcliffe效率系数（NSE）**

$$NSE = 1 - \frac{\sum_{m=1}^{12}(y_m - \hat{y}_m)^2}{\sum_{m=1}^{12}(y_m - \bar{y})^2}$$

解读：NSE=1为完美预测；NSE=0时模型等价于用均值预测；NSE<0时模型比均值预测更差。本研究要求NSE≥0.70（即模型比均值预测好70%以上）。

**指标3：月度Pearson相关系数（r）**

$$r = \frac{\sum(y_m - \bar{y})(\hat{y}_m - \hat{\bar{y}})}{\sqrt{\sum(y_m-\bar{y})^2}\sqrt{\sum(\hat{y}_m-\hat{\bar{y}})^2}}$$

要求r≥0.85，捕捉月度变化趋势的模拟能力。

**指标4：95%预测区间覆盖率（PI_Coverage）**

$$PI_{95\%} = \frac{\text{落入95\%预测区间的月份数}}{12} \times 100\%$$

要求PI_Coverage≥90%，验证不确定性量化的可靠性。

**指标5：百分位误差（P10/P90偏差）**

$$Bias_{P10} = \frac{\hat{y}_{P10} - y_{P10}}{y_{P10}} \times 100\%$$

检验模型在低排放月份（P10）和高排放月份（P90）的预测偏差，防止模型"中间好两头差"的问题。

### 5.3.3 验收标准矩阵

**表5-2 FPCM模型验收标准（按精度级别）**

| 评估指标 | Level 3验收标准 | Level 4验收标准 | 不合格判断 |
|---------|--------------|--------------|---------|
| 年度RE | [-15%, +15%] | [-10%, +10%] | |RE|>15%拒绝 |
| 月度NSE | ≥0.70 | ≥0.80 | NSE<0.60拒绝 |
| Pearson r | ≥0.85 | ≥0.90 | r<0.80拒绝 |
| PI_95%覆盖率 | ≥90% | ≥92% | <85%拒绝 |
| Scope 2 RE | [-10%, +10%] | [-8%, +8%] | |RE|>12%拒绝 |
| Scope 1 RE | [-30%, +30%] | [-20%, +20%] | |RE|>35%拒绝 |

---

## 5.4 本章小结

本章完成了FPCM全厂集成碳排放模型的完整数学规范和工程实现方案：

1. **集成形式**：将15个参数的代数方程体系整合为单一函数调用接口，支持单点计算（<0.01秒）和批量蒙特卡洛采样（10,000次约3分钟）；

2. **贝叶斯率定**：通过对数正态似然函数+NUTS-MCMC的完整实现，解决了参数辨识性不足、过拟合和非对称分布等传统率定的核心困难；

3. **收敛诊断**：建立了$\hat{R}$<1.01、ESS>400/chain、发散数<20等多指标收敛检验体系；

4. **验证方案**：采用时序感知的扩展窗口交叉验证，避免季节性自相关导致的信息泄露；建立了5项定量评估指标和分级验收标准，确保模型在独立测试集上的可信度。

---

*章节版本：v2.0 | 更新日期：2026-07-21 | 较v1.0新增：集成模型完整数学表达式、四级自适应形式化定义、NUTS代码完整实现（含先验参数化）、似然函数推导与正当性论证、收敛诊断标准、5项评估指标完整公式*
