# 第四章 碳排放子模型构建

## 4.1 建模总体框架与方法论选择

### 4.1.1 机理-经验混合建模的必要性论证

在轻量化数据约束下构建碳排放子模型，面临一个基本的方法论选择：纯机理模型（无经验参数）vs 纯经验模型（无物理约束）vs 机理-经验混合模型。三种方法的性质对比如表4-1所示：

**表4-1 三种建模策略的适用性分析**

| 建模策略 | 物理可解释性 | 轻量化数据适应性 | 参数需求量 | 外推可靠性 | 代表方法 |
|---------|-----------|---------------|----------|----------|---------|
| 纯机理模型 | 最强 | 差（需大量动力学参数）| 多（ASM2d-N₂O约50+）| 强 | ASM2d, ASM-N₂O |
| 纯经验/统计 | 差 | 好（有数据即可训练）| 少（特征数≈输入维度）| 弱（外推失效）| 随机森林、ANN |
| 机理-经验混合 | 中等（机理框架+经验修正）| **好**（机理约束减少数据需求）| **中等**（5～15个可率定参数）| **中等**（物理约束防止外推失效）| **本研究FPCM** |

混合建模的核心优势在于：机理方程提供物理约束（如质量守恒），防止模型在训练数据外产生非物理预测（如负排放量）；经验修正项（通常1～3个率定参数）吸收机理认知不完整带来的系统偏差（如N₂O排放因子的工厂间变异）。Brun等（2002）在水文建模领域的研究表明，当观测数据少于50个时，机理约束可将参数不确定性降低40%～60%，这一结论对本研究的轻量化数据场景具有直接参考价值。

### 4.1.2 各子模型的层次划分与方程形式

本研究6个子模型按机理化程度分为两类：

**A类（强机理，经验修正较少）**：M3（曝气能耗）、M4（其他能耗）  
这两类子模型的物理化学过程（需氧量计算、电力转化）成熟度高，文献中方程形式基本一致，不确定性主要来自工程参数（如传质系数α），经验修正项不超过2个。

**B类（弱机理，经验修正较多）**：M1（CH₄）、M2（N₂O）、M5（药剂）、M6（污泥）  
这类子模型的过程不确定性高，现有机理方程在轻量化数据条件下无法直接应用（缺少关键状态变量），需以更多的经验修正项（3～6个率定参数）来弥补机理简化的精度损失。

---

## 4.2 M1：CH₄排放子模型

### 4.2.1 建模逻辑链与方程推导

**逻辑链**：进水有机负荷（L-Core：Q_in, COD_in）→ 厌氧区可发酵底物量 → 温度调制的产甲烷速率 → 好氧区甲烷氧化消耗 → 最终大气逸散量

**步骤1：确定产甲烷底物量（以BOD当量表示）**

由于L-Core中无BOD₅数据，以COD替代并引入可生化降解比（f_BOD/COD）：

$$BOD_{in} = f_{BOD/COD} \times COD_{in} \quad (mg/L)$$

年总有机物投入（TOW，以BOD计）：

$$TOW = Q_{in,avg} \times BOD_{in} \times 365 \times 10^{-6} \quad (tBOD/年)$$

其中Q_in,avg为年均日进水量（m³/d），由12个月月均流量加权计算。

**步骤2：扣除随污泥稳定去除的有机物**

污泥处置（M6中计算）携带的有机物不参与产甲烷，需从TOW中扣除：

$$TOW_{avail} = TOW \times (1 - f_{sludge\_org})$$

$f_{sludge\_org}$（污泥有机物占进水BOD比例）的理论值由产泥系数估算：

$$f_{sludge\_org} = Y_{obs} \times 1.42 / f_{BOD/COD}$$

其中1.42 gCOD/gVSS为细胞氧当量，$Y_{obs}$（表观产泥系数）典型值0.35～0.50 kgVSS/kgBOD（AAO工艺在SRT=15～25 d时）。以Y_obs=0.42（先验均值），f_BOD/COD=0.48，得f_sludge_org≈0.248，即约25%的进水BOD以污泥形式去除。

**步骤3：温度修正函数**

产甲烷速率的温度依赖性采用改进型Arrhenius方程（参数化形式，避免活化能E_a难以标定的问题）：

$$f_T = \theta_{T}^{T - T_{ref}}$$

其中$\theta_T$（温度修正基数）的文献分布：Daelman等（2012）实测值为1.033（T_ref=15°C）；Metcalf & Eddy（2014）推荐值为1.04～1.08（T_ref=20°C）。本研究以T_ref=20°C，$\theta_T$先验均值取1.040，标准差0.012（正态分布，范围1.015～1.065）。

**步骤4：完整CH₄排放量方程**

$$E_{CH_4} = TOW_{avail} \times MCF \times B_0 \times f_T \times (1 - f_{rec}) \times GWP_{CH_4} \quad (\text{kgCO}_2\text{eq/年})$$

$$= Q_{in} \times COD_{in} \times 365 \times 10^{-6} \times f_{BOD/COD} \times (1 - f_{sludge\_org}) \times MCF \times B_0 \times \theta_T^{T-20} \times (1-f_{rec}) \times 28$$

**方程参数说明（表4-2）：**

**表4-2 M1子模型参数汇总**

| 符号 | 含义 | 默认值（先验均值）| 先验分布 | 文献范围 | 来源 |
|------|------|---------------|---------|---------|------|
| f_BOD/COD | BOD/COD比 | 0.48 | Normal(0.48, 0.07) | 0.35～0.65 | Tchobanoglous等（2014）|
| f_sludge_org | 污泥有机碳比 | 0.25 | Beta(5, 15) | 0.15～0.45 | 由Y_obs推算 |
| MCF | 甲烷修正因子 | 0.028 | LogNormal(ln0.028, 0.6) | 0.005～0.10 | Daelman等（2012）；Liu等（2015）|
| B₀ | 最大甲烷产生潜力 | 0.60 | Normal(0.60, 0.05) | 0.45～0.75 | IPCC（2019）|
| θ_T | 温度修正基数 | 1.040 | Normal(1.040, 0.012) | 1.015～1.065 | Metcalf & Eddy（2014）|
| f_rec | CH₄回收利用率 | 0 | — | 0（无厌氧消化）| 案例厂配置 |
| GWP_CH₄ | 甲烷增温潜势 | 28 | 固定 | — | IPCC AR5 |

### 4.2.2 CH₄模型的适用性边界

本模型适用条件：
- ✅ 纯好氧活性污泥系统（包括AAO），MCF ∈ [0, 0.1]
- ✅ 无配套厌氧消化（f_rec=0；若有消化，需用M6的沼气回收模块修正）
- ❌ 不适用于厌氧MBBR、厌氧膜反应器等以厌氧处理为主的工艺（MCF应取0.7～0.9）
- ⚠️ 当进水中工业废水比例>30%（COD/BOD>2.5）时，f_BOD/COD显著偏低，应增加BOD检测以精化该参数

---

## 4.3 M2：N₂O排放子模型（双路径混合模型）

### 4.3.1 模型设计的核心思路

N₂O子模型的设计面临一个根本困难：三条产生路径（第2.3.2节）均依赖无法由L-Core参数直接计算的中间变量（亚硝酸盐浓度NO₂⁻、AOB生物量X_AOB、N₂OR活性等）。本研究采用以下简化策略：

1. **将路径A（AOB羟胺）和路径B（AOB反硝化）合并**为"硝化关联N₂O"（M2-nit），因为两者均发生于好氧区且均受DO调制——这种合并使DO成为M2-nit的唯一调制变量，可由L-Core直接提供（L-Core中DO通过平均假设处理，L-Ext中可提供实测月均DO）；

2. **将路径C（异养不完全反硝化）独立**为"反硝化N₂O"（M2-denit），由缺氧区COD/TN比（可由L-Core直接计算）调制；

3. **引入DO依赖的路径切换函数**（Michaelis-Menten型），捕捉DO从高到低时N₂O从路径B主导向路径A+B共同强化的转变特征——这是本研究相比IPCC方法的核心改进点。

### 4.3.2 M2-nit：硝化N₂O模型

**（a）基础硝化量估算**

由L-Core的氨氮参数计算年硝化氮量（ΔN_nit，kgN/年）：

$$\Delta N_{nit} = (NH_3N_{in} - NH_3N_{out}) \times Q_{in} \times 365 \times 10^{-6} \times 1000 \quad (kgN/年)$$

注意：若NH3N_out接近0（硝化基本完全），则ΔN_nit ≈ NH3N_in × Q_in × 365 × 10⁻³。

**（b）DO依赖的路径切换函数**

基于文献中DO与N₂O排放因子的非单调关系（图4-1示意），设计以下分段Michaelis-Menten型切换函数：

当 DO ≤ DO_opt（约2.0 mg/L）时（路径B激活区间）：

$$f_{DO,nit}^{(below)} = 1 + \frac{(f_{max} - 1) \cdot (DO_{opt} - DO)}{K_{DO,high} + (DO_{opt} - DO)}$$

当 DO > DO_opt 时（高DO区，路径B受抑但路径A可能因羟胺低而减少）：

$$f_{DO,nit}^{(above)} = 1 - \frac{f_{decrease} \cdot (DO - DO_{opt})}{K_{DO,low} + (DO - DO_{opt})}$$

参数取值与来源：
- $DO_{opt}$：最优DO（N₂O最小），约1.8～2.2 mg/L（Ahn等，2010；Ribera-Guardia等，2014）
- $f_{max}$：低DO时的N₂O增强因子上限（约3.0，即DO→0时排放为最优DO的3倍）
- $K_{DO,high}$、$K_{DO,low}$：Michaelis常数，约0.8和1.5 mg/L

在L-Core场景（无DO数据）下，$f_{DO,nit}$ 设为1.0（即假设在最优DO附近运行），引入50%的N₂O附加不确定性；在L-Ext场景（有DO月均值）下，使用实测DO代入上式，不确定性降至25%。

**（c）M2-nit完整方程**

$$E_{N_2O,nit} = \Delta N_{nit} \times EF_{nit} \times f_{DO,nit}(DO) \times f_{aq} \times \frac{M_{N_2O}}{2 \cdot M_N}$$

$$= \Delta N_{nit} \times EF_{nit} \times f_{DO,nit} \times 1.20 \times \frac{44}{28} \quad (kgN_2O/年)$$

其中：
- $EF_{nit}$：基础硝化N₂O排放因子（kgN₂O-N/kgN_nitrified），先验为LogNormal(ln0.0035, 0.65)，覆盖文献范围0.001%～1.5%（占进水TN的比例，转换为每单位硝化氮时约0.0005～0.015）
- $f_{aq}=1.20$：出水溶解N₂O修正系数（出水溶解N₂O排放约为气相的20%，Daelman等，2013）
- $M_{N_2O}/2M_N = 44/28 = 1.571$：氮（N₂O-N）换算为N₂O的质量比

### 4.3.3 M2-denit：反硝化N₂O模型

**（a）反硝化量估算**

从L-Core参数估算缺氧区反硝化量（ΔN_denit，kgN/年）：

$$\Delta N_{denit} = \Delta N_{removed} \times f_{denit\_fraction}$$

$$\Delta N_{removed} = (TN_{in} - TN_{out}) \times Q_{in} \times 365 \times 10^{-6} \times 1000 \quad (kgN/年)$$

$f_{denit\_fraction}$（反硝化占总去氮的比例）：扣除同化去氮（微生物合成消耗的氮，约占进水TN的5%～10%）后，反硝化约占80%～90%，先验均值取0.85。

**（b）COD/TN比修正函数**

基于Pijuan等（2014）对5座全规模处理厂的拟合结果，建立反硝化N₂O排放因子与进水C/N比的修正关系：

$$g(COD/TN) = EF_{denit,ref} \times \left[1 + k_g \cdot \exp\left(-\frac{COD/TN - (COD/TN)_{crit}}{k_{CN}}\right)\right]$$

当COD/TN >> (COD/TN)_crit时，$g \to EF_{denit,ref}$（碳源充足，反硝化完全，N₂O排放接近最低值）；  
当COD/TN << (COD/TN)_crit时，$g \to EF_{denit,ref} \times (1 + k_g)$（碳源严重不足，N₂O最多可增加$k_g$倍）。

参数值：
- $EF_{denit,ref}$：参考排放因子（COD/TN=8时），先验LogNormal(ln0.0012, 0.55)，范围0.0003～0.008 kgN₂O-N/kgN_denitrified
- $(COD/TN)_{crit}$：临界C/N比，先验Normal(6.5, 1.5)，范围4～10
- $k_g$：低C/N时的倍增系数，先验Normal(2.0, 0.6)，范围0.5～4.0
- $k_{CN}$：过渡宽度参数，固定为1.5

**（c）M2-denit完整方程**

$$E_{N_2O,denit} = \Delta N_{denit} \times g(COD/TN) \times f_{aq} \times \frac{44}{28} \quad (kgN_2O/年)$$

### 4.3.4 总N₂O排放与碳当量

$$E_{N_2O,total} = E_{N_2O,nit} + E_{N_2O,denit} \quad (kgN_2O/年)$$

$$E_{N_2O,CO_2eq} = E_{N_2O,total} \times GWP_{N_2O} = E_{N_2O,total} \times 265 \quad (kgCO_2eq/年)$$

### 4.3.5 M2模型的创新性与局限性

**创新性**：引入DO依赖的路径切换函数，可以区分"缺DO引发的高N₂O"（好氧区DO不足）和"缺C引发的高N₂O"（反硝化不完全），并分别量化其贡献，比单一排放因子法更精准，比完整ASM-N₂O模型更轻便。

**局限性**：（1）路径A、B的合并忽略了亚硝酸盐积累程度的影响（亚硝酸盐是路径B的直接底物），这在进水NH₄⁺负荷突变时可能引入系统误差；（2）好氧区N₂O液相传质动力学未显式建模，以f_aq修正系数统一处理；（3）模型假设好氧区DO均匀分布，实际中DO的空间梯度（曝气头密度不均匀）可能使N₂O排放局部更高。

---

## 4.4 M3：曝气能耗子模型

### 4.4.1 正向计算法（有进出水水质数据时）

当L-Core数据完整时，通过需氧量反算法估算曝气能耗：

**实际需氧量（AOR）的完整推导：**

$$AOR = AOR_{carbon} + AOR_{nitrification} - AOR_{denitrification}$$

**碳化需氧量（kgO₂/d）：**

$$AOR_{carbon} = Q_{in} \times (COD_{in} - COD_{out}) \times a_{org} \times 10^{-3}$$

其中$a_{org}$（碳化耗氧系数）由质量守恒推导：

$$a_{org} = 1 - 1.42 \times Y_{obs} / f_{BOD/COD}$$

以$Y_{obs}$=0.42，$f_{BOD/COD}$=0.48：$a_{org}$ = 1 - 1.42×0.42/0.48 ≈ 0.757 kgO₂/kgCOD

**硝化需氧量（kgO₂/d）：**

$$AOR_{nitrification} = 4.33 \times Q_{in} \times (NH_3N_{in} - NH_3N_{out}) \times 10^{-3}$$

4.33 gO₂/gNH₄-N的推导：1 mol NH₄⁺（14 g N）→1 mol NO₃⁻，消耗1.5 mol O₂（1.5×32=48 g）+0.5 mol O₂用于NO₂→NO₃（0.5×32=16 g），合计64/14 = 4.57 gO₂/gN；扣除细胞合成消耗的NH₃约5%，修正后约4.33 gO₂/gN（Tchobanoglous等，2014第7章）。

**反硝化还氧量（kgO₂/d，负项）：**

$$AOR_{denitrification} = 2.86 \times Q_{in} \times \Delta TN_{denitrified} \times 10^{-3}$$

反硝化还原1 mol NO₃⁻（14 g N）相当于释放2 mol O₂（2×16=32 g O₂当量/14 g N = 2.29 gO₂/gN）；但考虑NO₃⁻来自NO₂⁻路径的部分，实际使用值为2.86 gO₂/gNO₃-N（基于电子平衡，Metcalf & Eddy，2014）。

**标准需氧量（SOR）和曝气能耗：**

$$SOR = AOR \times \frac{C_{s,20}^*}{\alpha \times F \times (\beta \times C_{s,T}^* - C_L)}$$

其中$C_{s,20}^* = 9.08$ mg/L（清水20°C饱和DO），典型修正系数：α=0.65，F=0.85，β=0.95，$C_L$=2.0 mg/L。

鼓风曝气系统效率：SOTE（标准条件下氧转移效率）≈20%，考虑管损和效率，鼓风机轴功率：

$$P_{blower} = \frac{SOR \times 10^3}{SOTE \times \eta_{blower} \times \rho_{air} \times 0.232} \quad (kW)$$

曝气年能耗：

$$E_{aer} = P_{blower} \times 24 \times 365 \quad (kWh/年)$$

**注**：在L-Core条件下，α、F等参数无法精确获取，以先验分布参数化（α~Normal(0.65, 0.07)，F~Normal(0.87, 0.05)），引入±12%的能耗不确定性。

### 4.4.2 反查法（仅有总电耗E_total时）

在Level 2以下（E_total已知但无详细水质），以电耗分配系数估算曝气电耗：

$$E_{aer} = E_{total} \times r_{aer}$$

$r_{aer}$（曝气电耗分配比例）的先验：基于Yang等（2020）对国内15座AAO处理厂的实测，$r_{aer}$均值0.576，标准差0.062，范围[0.50, 0.65]。

---

## 4.5 M4：其他能耗子模型

### 4.5.1 各子系统电耗估算

**水泵系统（提升泵+回流泵）：**

$$E_{pump} = E_{total} \times r_{pump}$$

从Yang等（2020）同一调研数据，$r_{pump}$均值0.183，标准差0.035；范围[0.12, 0.25]。

**污泥处理系统（脱水机为主）：**

$$E_{sludge\_proc} = W_{sludge\_wet} / \eta_{dewater} \times e_{dewater}$$

其中$\eta_{dewater}$（脱水效率，以kgDS/kWh计）≈15～25 kgDS/kWh（离心脱水机典型值）；轻量化数据框架下，以$E_{sludge} = E_{total} \times r_{sludge}$（$r_{sludge}$均值0.10）简化处理。

**搅拌及辅助设备：**

$$E_{misc} = E_{total} - E_{aer} - E_{pump} - E_{sludge\_proc}$$

### 4.5.2 能耗间接碳排放计算

$$E_{elec,CO_2eq} = E_{total} \times EF_{grid}$$

$$E_{grid} = 0.5839 \text{ kgCO}_2\text{/kWh（全国平均，2022年）}$$

区域电网排放因子差异显著：华北（以煤电为主）0.8025 kgCO₂/kWh；华南（水电比例高）0.5271 kgCO₂/kWh（生态环境部，2023）。本研究建议优先使用案例厂所在省域的电网排放因子，以降低EF_grid的不确定性（Sobol ST=0.43，是最大不确定性来源，详见第六章）。

---

## 4.6 M5：药剂投加碳排放子模型

### 4.6.1 有台账记录时的直接计算

$$E_{chem} = m_{PAC} \times EF_{PAC} + m_{carbon} \times EF_{carbon} + m_{disinfect} \times EF_{disinfect}$$

碳排放因子采用表2-4的Cradle-to-Gate值。

### 4.6.2 无台账时的工程估算

**PAC投加量估算**（化学除磷场景）：

基于PAC除磷的化学计量关系（Al:P摩尔比1.5:1），以及PAC（Al₂(OH)₃Cl₃，分子量174.5，含Al约15.6%）的Al含量，PAC理论投加量为：

$$m_{PAC} = \frac{\Delta P_{chem} \times Q_{in} \times 365 \times 10^{-3}}{0.156} \times r_{Al,extra}$$

其中：
- $\Delta P_{chem}$：需化学除磷量（mg P/L）= max(0, TP_in - TP_bio - TP_out)
- TP_bio（生物除磷量）≈ 0.015×MLSS（mg P/L，经验关系，Henze等，2000）
- $r_{Al,extra}$：过量投加系数（实际用量/理论用量，约1.5～2.5，考虑干扰离子和充分混合要求）

**外加碳源估算**（COD/TN<5时）：

当检测到COD/TN < 5时，估算需补充的碳源量：

$$m_{carbon} = Q_{in} \times TN_{denitrify} \times \left[(COD/TN)_{target} - COD/TN\right] / \eta_{carbon} \times 365 \times 10^{-3}$$

其中$(COD/TN)_{target}$取5.5（工程安全裕量），$\eta_{carbon}$（碳源利用效率，典型0.85）。

---

## 4.7 M6：污泥处置碳排放子模型

### 4.7.1 干污泥量的确定

模型以**干固体质量（tDS/年）**作为污泥碳排放的计算基准，获取途径有三：

**方法1（最优）**：直接来自L-Core的W_sludge（月外排污泥干重台账）：

$$W_{sludge,annual} = \sum_{m=1}^{12} W_{sludge,m} \quad (tDS/年)$$

**方法2（W_sludge缺失时）**：通过污泥湿重×(1-MC)计算，MC为含水率：

$$W_{DS} = W_{wet} \times (1 - MC_{sludge})$$

脱水后污泥典型含水率：离心脱水后80%～82%，板框压滤后60%～65%。

**方法3（全无数据时）**：通过物料守恒估算：

$$W_{DS} = Q_{in} \times (SS_{in} - SS_{out} + VSS_{biosynthesis}) \times 10^{-6} \times 365$$

其中生化合成VSS量≈$Y_{obs} \times (BOD_{in} - BOD_{out}) \times Q_{in}$。

### 4.7.2 处置方式碳排放因子的不确定性分析

碳排放因子（EF_disposal）在不同处置方式间的差异高达5倍（50～1,200 kgCO₂eq/tDS），且同一方式内由于运营条件不同也存在±30%～±50%的变化。这是Scope 3污泥排放不确定性高的根本原因。

为降低不确定性，本研究建立分情景的EF_disposal先验分布（表4-3）：

**表4-3 各处置方式EF_disposal先验分布参数**

| 处置方式 | 先验均值（kgCO₂eq/tDS）| 先验标准差 | 分布类型 | 中国主要来源 |
|---------|-------------------|---------|---------|-----------|
| 好氧堆肥（封闭） | 360 | 90 | LogNormal | 张等（2022），10座中国堆肥厂 |
| 好氧堆肥（开放）| 480 | 130 | LogNormal | 同上（开放式更多N₂O逸散） |
| 厌氧消化+沼气发电 | 100 | 55 | LogNormal | 王等（2021），沼气回收率75% |
| 卫生填埋（有截气）| 680 | 180 | LogNormal | 宋等（2020），填埋气回收60% |
| 卫生填埋（无截气）| 950 | 240 | LogNormal | 同上（无回收）|
| 焚烧（干化后）| 980 | 220 | LogNormal | 刘等（2021）|
| 土地直接施用 | 120 | 180 | Normal（允许负值）| 固碳效应，变化大 |

---

## 4.8 子模型参数汇总与率定接口

**表4-4 全模型可率定参数完整清单**

| 参数符号 | 所属模型 | 先验类型 | 先验均值 | 先验σ | 范围下限 | 范围上限 | 物理含义 |
|---------|---------|---------|---------|-------|---------|---------|---------|
| f_BOD/COD | M1 | Normal | 0.48 | 0.07 | 0.35 | 0.65 | BOD/COD比值 |
| MCF | M1 | LogNormal | 0.028 | 0.60* | 0.005 | 0.10 | 甲烷修正因子 |
| B₀ | M1 | Normal | 0.60 | 0.05 | 0.45 | 0.75 | 最大甲烷产生潜力 |
| θ_T | M1 | Normal | 1.040 | 0.012 | 1.015 | 1.065 | 温度修正基数 |
| EF_nit | M2-nit | LogNormal | 0.0035 | 0.65* | 0.0005 | 0.015 | 硝化N₂O排放因子 |
| DO_opt | M2-nit | Normal | 2.0 | 0.3 | 1.0 | 3.0 | 最优DO（N₂O最小）|
| f_max | M2-nit | LogNormal | 3.0 | 0.4* | 1.5 | 6.0 | 低DO增强因子 |
| EF_denit,ref | M2-denit | LogNormal | 0.0012 | 0.55* | 0.0003 | 0.008 | 反硝化参考排放因子 |
| (C/N)_crit | M2-denit | Normal | 6.5 | 1.5 | 3.5 | 10.0 | 临界C/N比 |
| k_g | M2-denit | Normal | 2.0 | 0.6 | 0.5 | 4.0 | C/N不足时增强倍数 |
| α | M3 | Normal | 0.65 | 0.07 | 0.45 | 0.80 | 污水传质修正系数 |
| r_aer | M3/M4 | Normal | 0.576 | 0.062 | 0.50 | 0.65 | 曝气电耗分配比 |
| EF_grid | M3/M4 | Normal | 0.5839 | 0.03 | — | — | 电网排放因子 |
| Y_obs | M6 | Beta | 0.42 | 0.06 | 0.30 | 0.55 | 表观产泥系数 |
| EF_disposal | M6 | 见表4-3 | — | — | — | — | 污泥处置因子 |

注：*LogNormal分布中的σ为对数空间的标准差（σ_ln）。

## 4.9 本章小结

本章完成了FPCM的6个核心子模型的建立与参数化，主要贡献包括：

1. **M1（CH₄）**：在IPCC Tier 2框架上引入参数化MCF先验（LogNormal分布，均值0.028，覆盖中国管网CH₄输入特征）和Arrhenius温度修正，参数可率定；

2. **M2（N₂O）**：创新性地构建了双路径模型，M2-nit引入DO依赖的Michaelis-Menten型路径切换函数（参数$DO_{opt}$、$f_{max}$），M2-denit引入COD/TN修正函数（参数$(C/N)_{crit}$、$k_g$），可捕捉中国北方低C/N进水导致N₂O升高的机理；

3. **M3/M4（能耗）**：提供正向AOR反算法和反查分配系数两种方案，适应不同数据完整性；

4. **M5/M6（药剂/污泥）**：建立有台账和无台账两种接口，M6的处置方式分情景EF先验分布为贝叶斯率定提供了充分的参数范围；

5. **完整参数清单**：汇总15个可率定参数及其先验分布，为第五章贝叶斯NUTS-MCMC率定提供完整规范。

---

*章节版本：v2.0 | 更新日期：2026-07-21 | 较v1.0新增：建模策略比较表、CH₄完整方程推导（含TOW物料守恒）、N₂O路径切换函数的数学表达、AOR各分项推导（4.33 gO₂/gN来源论证）、药剂估算化学计量推导、污泥量三方法层次、15参数完整先验分布汇总*
