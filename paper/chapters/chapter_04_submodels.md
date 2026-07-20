# 第四章 碳排放子模型构建

## 4.1 建模总体框架

### 4.1.1 子模型设计原则

本章构建的碳排放子模型遵循以下设计原则：

1. **轻量化数据兼容**：所有子模型的输入变量均来自第三章确定的L-Core或L-Ext参数集；
2. **机理-经验混合**：对于机理清晰的过程（如曝气能耗）采用机理方程；对于高不确定性的过程（如N₂O产生）采用经验修正项；
3. **参数可率定**：每个子模型均设计可调参数接口，支持基于实测数据的贝叶斯率定；
4. **独立验证**：每个子模型可独立进行验证，不依赖其他子模型的输出；
5. **计算效率**：避免偏微分方程等高计算代价方法，优先采用代数方程或简单常微分方程。

### 4.1.2 子模型列表与数据流

```
输入数据（L-Core + L-Ext）
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
[M1: CH₄子模型]    [M2: N₂O子模型]
    │               │
    ▼               ▼
E_CH4(kgCH4/年)   E_N2O(kgN2O/年)
    │               │
    └───────┬───────┘
            ▼
       [GWP换算]
            │
            ▼
      Scope1_CO2eq
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
[M3: 曝气能耗模型]  [M4: 其他能耗模型]
    │               │
    └───────┬───────┘
            ▼
       Scope2_CO2eq
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
[M5: 药剂排放模型]  [M6: 污泥处置模型]
    │               │
    └───────┬───────┘
            ▼
       Scope3_CO2eq
            │
            ▼
    E_total = Scope1 + Scope2 + Scope3
```

---

## 4.2 CH₄排放模型（M1）

### 4.2.1 模型描述

AAO工艺中CH₄的主要排放场景是厌氧池及进水管网。本模型采用IPCC Tier 2框架，结合温度修正和工艺参数调整：

### 4.2.2 模型方程

**步骤1：计算年度可降解有机物总量（TOW）**

$$TOW = Q_{in} \times BOD_{in} \times 365 \times 10^{-6} \quad [\text{tBOD/年}]$$

若BOD₅数据缺失，使用COD代替（需引入BOD:COD转换系数 $f_{BOD/COD}$）：

$$BOD_{in} = f_{BOD/COD} \times COD_{in}, \quad f_{BOD/COD} \in [0.4, 0.6]$$

**步骤2：计算随污泥去除的有机物**

$$S_{removed} = TOW \times f_{sludge} \quad [f_{sludge} \approx 0.2 \sim 0.35]$$

**步骤3：温度修正系数**

产甲烷速率随温度变化，采用Arrhenius型修正：

$$\theta_{T} = \exp\left[\frac{E_a}{R}\left(\frac{1}{T_{ref}} - \frac{1}{T}\right)\right]$$

简化为经验公式（默认参考温度25°C）：

$$\theta_T = 1.04^{(T-25)}, \quad T \in [10, 35]\text{°C}$$

**步骤4：CH₄年排放量计算**

$$E_{CH_4} = (TOW - S_{removed}) \times MCF \times B_0 \times \theta_T \times (1 - f_{rec}) \times \rho_{CH_4}$$

$$[\text{单位：kgCH}_4/\text{年}]$$

其中：
| 参数 | 符号 | 默认值 | 说明 |
|------|------|-------|------|
| 甲烷修正因子 | MCF | 0.03 | 好氧活性污泥系统（IPCC：0.0～0.1） |
| 最大甲烷产生潜力 | B₀ | 0.6 | kgCH₄/kgBOD（IPCC默认值） |
| CH₄回收比例 | f_rec | 0 | 无厌氧消化回收时为0 |
| CH₄密度 | ρ_CH₄ | 0.67 | kg/m³（标准状态） |

### 4.2.3 可率定参数

| 参数 | 符号 | 先验分布 | 范围 |
|------|------|---------|------|
| 甲烷修正因子 | MCF | Beta(2,40) | [0.0, 0.15] |
| BOD:COD比 | f_BOD/COD | Normal(0.50, 0.07) | [0.35, 0.65] |
| 污泥有机物去除比 | f_sludge | Beta(5,15) | [0.15, 0.45] |
| 温度修正基数 | θ_base | Normal(1.04, 0.01) | [1.02, 1.06] |

### 4.2.4 Python实现伪代码

```python
def calc_ch4_emission(Q_in, COD_in, MLSS, T=20, 
                       f_boc=0.50, MCF=0.03, B0=0.6,
                       f_sludge=0.25, f_rec=0.0):
    """
    计算AAO工艺年度CH4排放量
    Returns: E_CH4 [kgCH4/year]
    """
    BOD_in = f_boc * COD_in  # mg/L
    TOW = Q_in * BOD_in * 365 * 1e-6  # tBOD/year
    S_removed = TOW * f_sludge
    theta_T = 1.04 ** (T - 25)
    E_CH4 = (TOW - S_removed) * MCF * B0 * theta_T * (1 - f_rec) * 1000  
    # 单位：kgCH4/year（TOW单位tBOD，需×1000）
    return E_CH4
```

---

## 4.3 N₂O排放模型（M2）

### 4.3.1 模型结构

N₂O排放来自两个路径的叠加：
- **路径A**：硝化过程N₂O（好氧区AOB副反应）
- **路径B**：反硝化过程N₂O（缺氧区不完全反硝化）

$$E_{N_2O,total} = E_{N_2O,A} + E_{N_2O,B}$$

### 4.3.2 路径A：硝化N₂O模型

硝化N₂O排放量与被硝化的氨氮量成正比，但受DO和亚硝酸盐积累的非线性调制：

**硝化量估算：**

$$\Delta N_{nit} = (NH_{3}N_{in} - NH_{3}N_{out}) \times Q_{in} \times 365 \times 10^{-6} \quad [\text{tN/年}]$$

**DO修正因子（Kampschreur等，2009的经验关系）：**

$$f_{DO} = \frac{K_{DO,N_2O}}{K_{DO,N_2O} + DO} \quad [\text{低DO促进N}_2\text{O}]$$

推荐值：$K_{DO,N_2O} = 1.5$ mg/L（文献范围：0.5～3.0 mg/L）

**路径A的N₂O排放：**

$$E_{N_2O,A} = \Delta N_{nit} \times EF_{nit} \times f_{DO} \times \frac{M_{N_2O}}{2M_N}$$

其中：
- $EF_{nit}$：硝化N₂O排放因子，默认0.0032 kgN₂O-N/kgN_nitrified（文献中位值）
- $\frac{M_{N_2O}}{2M_N} = \frac{44}{28} = 1.571$：氮换算为N₂O的质量转换系数

### 4.3.3 路径B：反硝化N₂O模型

反硝化N₂O排放与脱氮量和碳源充足性相关：

**脱氮量估算：**

$$\Delta N_{denit} = TN_{in} - TN_{out} - \Delta N_{nit} \quad [\text{注：考虑同化去氮}]$$

实际简化：
$$\Delta N_{denit} = (TN_{in} - TN_{out}) \times Q_{in} \times 365 \times 10^{-6} \times f_{denit} \quad [\text{tN/年}]$$

其中 $f_{denit} \approx 0.85$（约85%的去除TN来自反硝化）。

**C/N比修正因子（碳源充足性）：**

$$f_{CN} = 1 - \exp\left(-\frac{COD_{in}/TN_{in}}{(COD/TN)_{critical}}\right)$$

$(COD/TN)_{critical} \approx 8$（低于此值时反硝化不完全加剧）

**路径B的N₂O排放：**

$$E_{N_2O,B} = \Delta N_{denit} \times EF_{denit} \times (2 - f_{CN}) \times \frac{M_{N_2O}}{2M_N}$$

其中 $EF_{denit} = 0.0016$ kgN₂O-N/kgN_denitrified（Daelman等，2015默认值）。

### 4.3.4 总N₂O排放与CO₂当量

$$E_{N_2O,total} = E_{N_2O,A} + E_{N_2O,B} \quad [\text{kgN}_2\text{O/年}]$$

$$E_{N_2O,CO_2eq} = E_{N_2O,total} \times GWP_{N_2O} = E_{N_2O,total} \times 265 \quad [\text{kgCO}_2\text{eq/年}]$$

### 4.3.5 可率定参数

| 参数 | 符号 | 先验分布 | 范围 |
|------|------|---------|------|
| 硝化N₂O排放因子 | EF_nit | LogNormal(0.0032, 0.6) | [0.0005, 0.015] |
| 反硝化N₂O排放因子 | EF_denit | LogNormal(0.0016, 0.6) | [0.0003, 0.008] |
| DO半饱和常数 | K_DO | Normal(1.5, 0.5) | [0.3, 3.0] |
| C/N临界值 | CN_critical | Normal(8, 2) | [5, 12] |

---

## 4.4 曝气能耗模型（M3）

### 4.4.1 模型思路

在缺乏曝气量实测数据的条件下，通过**氧化需氧量（OD）**反算理论需气量，再结合鼓风机效率估算能耗：

### 4.4.2 需氧量计算

**总需氧量（AOR）**包括：碳化需氧量 + 硝化需氧量 − 反硝化还氧量：

$$AOR = 1.47 \times \Delta BOD - 1.14 \times \Delta NO_3 + 4.57 \times \Delta NH_4$$

简化为常用工程公式（适用于AAO工艺，单位 kgO₂/d）：

$$AOR = Q_{in} \times \left[a \times (S_0 - S_e) + b \times X_v + c \times \Delta N_{nit} - d \times \Delta N_{denit}\right] \times 10^{-3}$$

其中：
- $a = 1.47$：碳化耗氧系数（kgO₂/kgBOD）
- $b = 0.1$：内源呼吸耗氧系数（kgO₂/(kgMLVSS·d)）
- $c = 4.33$：硝化耗氧系数（kgO₂/kgNH₃-N氧化）
- $d = 2.86$：反硝化还氧系数（kgO₂/kgNO₃-N）

### 4.4.3 曝气能耗计算

**标准需氧量（SOR）**通过以下修正将AOR转换为标准状态下的需氧量：

$$SOR = AOR \times \frac{C_s^{20}}{(\beta \times C_{sw} - C_L) \times \alpha \times F}$$

典型参数：
- $C_s^{20} = 9.08$ mg/L（20°C清水饱和溶解氧）
- $\beta = 0.95$（污水修正系数）
- $\alpha = 0.7$（传质修正系数）
- $F = 0.9$（曝气器污染修正系数）
- $C_L = 2.0$ mg/L（运行DO控制值）

**曝气电耗（轻量化简化方法）：**

当详细曝气参数不可获取时，使用**电耗强度因子**方法：

$$E_{aer} = Q_{in} \times e_{aer} \times 365 \quad [\text{kWh/年}]$$

其中 $e_{aer}$（kWh/m³进水）为曝气电耗强度，由以下关系确定：

$$e_{aer} = k_{aer} \times \frac{TN_{in}}{f_{nit}} + k_{BOD} \times COD_{in}$$

其中 $k_{aer}$ 和 $k_{BOD}$ 为率定参数，参考文献典型值 $k_{aer} \approx 0.015$，$k_{BOD} \approx 0.0004$。

**曝气间接碳排放：**

$$E_{aer,CO_2} = E_{aer} \times EF_{grid} \quad [\text{kgCO}_2/\text{年}]$$

---

## 4.5 其他能耗模型（M4）

在仅有全厂总电耗数据（E_total）的轻量化场景下，通过电耗分配系数估算各子系统能耗：

### 4.5.1 基于总电耗的分配方法

$$E_{pump} = E_{total} \times r_{pump}$$
$$E_{mix} = E_{total} \times r_{mix}$$
$$E_{sludge} = E_{total} \times r_{sludge}$$
$$E_{other} = E_{total} \times r_{other}$$

典型分配比（来自文献调研）：

| 子系统 | 分配比 r | 范围 |
|--------|---------|------|
| 曝气系统 | 0.58 | 0.50～0.65 |
| 水泵系统 | 0.18 | 0.12～0.25 |
| 污泥处理 | 0.10 | 0.08～0.15 |
| 搅拌设备 | 0.04 | 0.02～0.06 |
| 其他辅助 | 0.10 | 0.05～0.15 |

**非曝气能耗间接碳排放：**

$$E_{other,CO_2} = (E_{total} - E_{aer}) \times EF_{grid}$$

---

## 4.6 药剂投加碳排放模型（M5）

### 4.6.1 模型方程

$$E_{chem} = \sum_{j} m_j \times EF_{chem,j}$$

其中 $m_j$ 为药剂 j 的年投加量（kg/年），$EF_{chem,j}$ 为其碳排放因子。

### 4.6.2 药剂用量估算

在缺乏药剂投加量记录时，通过以下经验关系估算：

**PAC用量估算（化学除磷）：**

$$m_{PAC} = Q_{in} \times \max(0, TP_{in} - TP_{out}) \times r_{PAC} \times 365 \times 10^{-3}$$

其中 $r_{PAC} \approx 3.0$ kgPAC/kgTP-removed（PAC化学计量比经验值）。

**外加碳源用量估算：**

仅在 $COD_{in}/TN_{in} < 5$（碳源不足时）时有外加碳源投加：

$$m_{carbon} = Q_{in} \times TN_{in} \times \max\left(0, \frac{5 - COD_{in}/TN_{in}}{1000}\right) \times k_{carbon} \times 365$$

其中 $k_{carbon}$ 为单位脱氮所需碳源量的率定系数。

### 4.6.3 药剂碳排放汇总

$$E_{chem} = m_{PAC} \times 1.3 + m_{carbon} \times EF_{carbon} + m_{disinfect} \times EF_{disinfect}$$

---

## 4.7 污泥处理碳排放模型（M6）

### 4.7.1 污泥产量计算

在仅有MLSS数据时，通过物料守恒估算污泥产量：

$$\dot{P}_{sludge} = Y_{obs} \times Q_{in} \times (COD_{in} - COD_{out}) \times 10^{-3}$$

其中 $Y_{obs}$（表观产泥系数）的范围为0.3～0.5 kgVSS/kgCOD。

### 4.7.2 不同处置方式的碳排放因子

根据污水处理厂实际污泥处置方式选择对应排放因子：

$$E_{sludge} = W_{sludge} \times EF_{disposal}$$

其中 $EF_{disposal}$（kgCO₂eq/tDS）：

| 处置方式 | EF值 | 文献来源 |
|---------|------|---------|
| 卫生填埋（有覆盖） | 800 | Wang等，2019 |
| 好氧堆肥 | 450 | Xu等，2018 |
| 厌氧消化+土地利用 | 200 | Colón等，2012 |
| 焚烧 | 1100 | Song等，2020 |
| 建材利用（干化焚烧）| 650 | 自整理 |

---

## 4.8 本章小结

本章构建了AAO工艺全厂碳排放的6个子模型：

1. **M1（CH₄模型）**：基于IPCC Tier 2框架，引入温度修正，适配BOD或COD输入；
2. **M2（N₂O模型）**：分硝化路径（A）和反硝化路径（B），通过DO修正因子和C/N修正因子捕捉关键影响；
3. **M3（曝气能耗）**：提供需氧量反算法和电耗强度因子法两种方案；
4. **M4（其他能耗）**：基于总电耗分配系数方法简化计算；
5. **M5（药剂排放）**：提供药剂用量实测和经验估算两种接口；
6. **M6（污泥处置）**：基于处置方式选择对应排放因子。

每个子模型均识别了可率定参数及其先验分布，为第五章贝叶斯参数率定提供基础。

---

*章节版本：v1.0 | 更新日期：2026-07-21*
