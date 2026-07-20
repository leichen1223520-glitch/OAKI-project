# 附录

## 附录A 符号与缩写表

### A.1 缩写列表

| 缩写 | 全称（英文） | 中文 |
|------|------------|------|
| AAO | Anaerobic-Anoxic-Oxic | 厌氧-缺氧-好氧工艺 |
| AOB | Ammonia-Oxidizing Bacteria | 氨氧化菌 |
| NOB | Nitrite-Oxidizing Bacteria | 亚硝酸盐氧化菌 |
| PAO | Phosphorus-Accumulating Organisms | 聚磷菌 |
| ASM | Activated Sludge Model | 活性污泥模型 |
| GHG | Greenhouse Gas | 温室气体 |
| GWP | Global Warming Potential | 全球增温潜势 |
| IPCC | Intergovernmental Panel on Climate Change | 政府间气候变化专门委员会 |
| LCA | Life Cycle Assessment | 生命周期评估 |
| MCMC | Markov Chain Monte Carlo | 马尔可夫链蒙特卡洛 |
| MCF | Methane Correction Factor | 甲烷修正因子 |
| MLSS | Mixed Liquor Suspended Solids | 混合液悬浮固体 |
| MLVSS | Mixed Liquor Volatile Suspended Solids | 混合液挥发性悬浮固体 |
| NSE | Nash-Sutcliffe Efficiency | Nash-Sutcliffe效率系数 |
| NUTS | No-U-Turn Sampler | MCMC算法名 |
| ORP | Oxidation-Reduction Potential | 氧化还原电位 |
| PAC | Polyaluminum Chloride | 聚合氯化铝 |
| PINN | Physics-Informed Neural Network | 物理信息神经网络 |
| RE | Relative Error | 相对误差 |
| RBF | Radial Basis Function | 径向基函数 |
| RMSE | Root Mean Square Error | 均方根误差 |
| SRT | Sludge Retention Time | 污泥龄 |
| HRT | Hydraulic Retention Time | 水力停留时间 |
| VFA | Volatile Fatty Acids | 挥发性脂肪酸 |
| WWTP | Wastewater Treatment Plant | 污水处理厂 |
| FPCM | Full-Plant Carbon emission Model | 全厂碳排放模型（本研究） |
| L-Core | Lightweight Core Parameter Set | 轻量化核心参数集（本研究） |
| L-Ext | Lightweight Extended Parameter Set | 轻量化扩展参数集（本研究） |
| MVMS | Minimum Viable Monitoring Set | 最小可行监测参数集（本研究） |

### A.2 主要符号列表

| 符号 | 含义 | 单位 |
|------|------|------|
| $Q_{in}$ | 进水流量 | m³/d |
| $COD_{in/out}$ | 进/出水COD | mg/L |
| $TN_{in/out}$ | 进/出水总氮 | mg/L |
| $NH_3N_{in/out}$ | 进/出水氨氮 | mg/L |
| $DO$ | 溶解氧 | mg/L |
| $T$ | 水温 | °C |
| $E_{CH_4}$ | CH₄年排放量 | kgCH₄/年 |
| $E_{N_2O}$ | N₂O年排放量 | kgN₂O/年 |
| $E_{total}$ | 全厂年碳排放总量 | kgCO₂eq/年 |
| $MCF$ | 甲烷修正因子 | — |
| $B_0$ | 最大甲烷产生潜力 | kgCH₄/kgBOD |
| $EF_{nit}$ | 硝化N₂O排放因子 | kgN₂O-N/kgN_nitrified |
| $EF_{denit}$ | 反硝化N₂O排放因子 | kgN₂O-N/kgN_denitrified |
| $EF_{grid}$ | 电网碳排放因子 | kgCO₂/kWh |
| $GWP$ | 全球增温潜势（100年）| — |
| $S_i$ | Sobol一阶灵敏度指数 | — |
| $S_{T_i}$ | Sobol总效应指数 | — |
| $\mu^*$ | Morris分析基本效应均值 | — |
| $\theta_T$ | 温度修正系数 | — |

---

## 附录B 模型代码说明

### B.1 代码结构

```
src/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── ch4_model.py          # M1: CH₄排放子模型
│   ├── n2o_model.py          # M2: N₂O排放子模型
│   ├── energy_model.py       # M3+M4: 能耗子模型
│   ├── chemical_model.py     # M5: 药剂排放子模型
│   ├── sludge_model.py       # M6: 污泥处置子模型
│   └── integrated_model.py   # FPCM集成框架
├── preprocessing/
│   ├── __init__.py
│   ├── data_validator.py     # 输入数据验证与质控
│   ├── missing_handler.py    # 缺失值处理策略
│   └── data_loader.py        # 数据读取接口（CSV/Excel）
├── calibration/
│   ├── __init__.py
│   ├── bayesian_calibration.py  # 贝叶斯参数率定（PyMC）
│   └── prior_distributions.py  # 参数先验分布定义
├── analysis/
│   ├── __init__.py
│   ├── sensitivity_analysis.py  # Morris + Sobol分析（SALib）
│   └── uncertainty_analysis.py  # 蒙特卡洛不确定性传播
└── utils/
    ├── __init__.py
    ├── constants.py          # GWP、排放因子等常量
    ├── unit_converter.py     # 单位换算工具
    └── report_generator.py   # 碳排放报告生成
```

### B.2 快速使用示例

```python
from src.models.integrated_model import FPCM
from src.models.integrated_model import ModelInput

# 构建输入数据
input_data = ModelInput(
    Q_in=68000,          # m³/d
    COD_in=285,          # mg/L
    TN_in=38.5,          # mg/L
    TN_out=6.5,          # mg/L
    NH3N_in=28.3,        # mg/L
    NH3N_out=1.2,        # mg/L
    SS_in=220,           # mg/L
    MLSS=4200,           # mg/L
    E_total_monthly=890000,  # kWh/月
    W_sludge_monthly=168,    # tDS/月
    sludge_disposal="compost"
)

# 运行集成模型
model = FPCM()
result = model.run(input_data)

# 输出结果
print(f"全厂年度碳排放：{result.E_total_CO2eq/1000:.1f} tCO₂eq/年")
print(f"Scope 1：{result.E_Scope1_CO2eq/1000:.1f} tCO₂eq")
print(f"Scope 2：{result.E_Scope2_CO2eq/1000:.1f} tCO₂eq")
print(f"Scope 3：{result.E_Scope3_CO2eq/1000:.1f} tCO₂eq")
print(f"单位碳排放：{result.E_unit_kgCO2_m3:.3f} kgCO₂eq/m³")
print(f"计算精度级别：Level {result.calculation_level}")
print(f"预估不确定性：±{result.uncertainty_pct:.0f}%")
```

### B.3 环境配置

```bash
# 克隆仓库
git clone https://github.com/leichen1223520-glitch/OAKI-project.git
cd OAKI-project

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行示例
python notebooks/example_basic_calculation.ipynb
```

---

## 附录C 数据字典（完整版）

> 完整数据字典详见：`data/schema/data_dictionary.md`

### C.1 核心参数（L-Core）快速参考

| 参数 | 符号 | 单位 | 典型范围（城市污水） |
|------|------|------|------------------|
| 进水流量 | Q_in | m³/d | 5,000～200,000 |
| 进水COD | COD_in | mg/L | 150～500 |
| 进水总氮 | TN_in | mg/L | 20～70 |
| 进水氨氮 | NH₃N_in | mg/L | 15～55 |
| 出水总氮 | TN_out | mg/L | 1～15 |
| 出水氨氮 | NH₃N_out | mg/L | 0.1～5 |
| 进水SS | SS_in | mg/L | 100～400 |
| 好氧区MLSS | MLSS | mg/L | 2,500～6,000 |
| 月总电耗 | E_total | kWh/月 | 10～600 kWh/千m³ |
| 月污泥产量 | W_sludge | tDS/月 | — |

### C.2 排放因子快速参考（中国本土化）

| 排放因子 | 推荐值 | 单位 | 说明 |
|---------|-------|------|------|
| 电网排放因子 | 0.5839 | kgCO₂/kWh | 2022年全国平均 |
| 华北电网 | 0.8025 | kgCO₂/kWh | 煤电比例高 |
| 华南电网 | 0.5271 | kgCO₂/kWh | 水电比例较高 |
| GWP CH₄ | 28 | — | IPCC AR5，100年 |
| GWP N₂O | 265 | — | IPCC AR5，100年 |

---

*附录版本：v1.0 | 更新日期：2026-07-21*
