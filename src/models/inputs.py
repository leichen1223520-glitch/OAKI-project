"""
FPCM 模型输入/输出数据结构定义
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ModelInput:
    """
    FPCM 单次（月度或年度）运行输入数据。

    L-Core（必填，10项）：Q_in, E_total_monthly, COD_in, TN_in,
                          NH3N_in, NH3N_out, TP_in, COD_out, TN_out, T_water
    L-Ext（可选扩展）：DO_aer, MLSS, SRT, W_sludge, PAC_monthly, carbon_dose_monthly
    """
    # ── L-Core ───────────────────────────────────────────────
    Q_in: float = 0.0          # 日均进水量 (m³/d)
    E_total_monthly: float = 0.0  # 月电耗 (kWh/月)
    COD_in: float = 0.0        # 进水COD (mg/L)
    TN_in: float = 0.0         # 进水总氮 (mg/L)
    NH3N_in: float = 0.0       # 进水氨氮 (mg/L)
    NH3N_out: float = 0.0      # 出水氨氮 (mg/L)
    TP_in: float = 0.0         # 进水总磷 (mg/L)
    COD_out: float = 0.0       # 出水COD (mg/L)
    TN_out: float = 0.0        # 出水总氮 (mg/L)
    T_water: float = 20.0      # 水温 (°C)，默认20°C

    # ── L-Ext（可选扩展参数）────────────────────────────────
    DO_aer: Optional[float] = None       # 好氧区实测月均DO (mg/L)
    MLSS: Optional[float] = None         # 混合液悬浮固体 (mg/L)
    SRT: Optional[float] = None          # 污泥龄 (d)
    W_sludge: Optional[float] = None     # 月外排污泥干重 (tDS/月)
    W_sludge_wet: Optional[float] = None # 月外排污泥湿重 (t/月)
    PAC_monthly: Optional[float] = None  # 月PAC用量 (kg/月)
    carbon_dose_monthly: Optional[float] = None  # 月外加碳源用量 (kg/月)
    SS_in: Optional[float] = None        # 进水SS (mg/L)
    SS_out: Optional[float] = None       # 出水SS (mg/L)

    # ── 处置配置 ─────────────────────────────────────────────
    disposal_method: str = "compost_closed"  # 污泥处置方式
    # 可选值: compost_closed, compost_open, anaerobic_digestion,
    #         landfill_gas, landfill_no_gas, incineration, land_application


@dataclass
class ModelOutput:
    """FPCM 计算结果"""
    E_CH4_kg: float = 0.0          # CH₄排放量 (kgCH₄/年)
    E_N2O_kg: float = 0.0          # N₂O排放量 (kgN₂O/年)
    E_Scope1_CO2eq: float = 0.0    # Scope1 直接排放 (kgCO₂eq/年)

    E_total_kWh: float = 0.0       # 年总电耗 (kWh/年)
    E_Scope2_CO2eq: float = 0.0    # Scope2 电力间接排放 (kgCO₂eq/年)

    E_chem_CO2eq: float = 0.0      # 药剂碳排放 (kgCO₂eq/年)
    E_sludge_CO2eq: float = 0.0    # 污泥处置碳排放 (kgCO₂eq/年)
    E_Scope3_CO2eq: float = 0.0    # Scope3 其他间接排放 (kgCO₂eq/年)

    E_total_CO2eq: float = 0.0     # 全厂总碳排放 (kgCO₂eq/年)
    E_unit_kgCO2_m3: float = 0.0   # 单位水量碳排放 (kgCO₂eq/m³)

    # 各子模型中间结果
    TOW: float = 0.0               # 总有机物投入 (tBOD/年)
    E_CH4_nit: float = 0.0         # 硝化N₂O排放 (kgN₂O/年)
    E_CH4_denit: float = 0.0       # 反硝化N₂O排放 (kgN₂O/年)
    E_aer_CO2eq: float = 0.0       # 曝气电力碳排放 (kgCO₂eq/年)
    W_DS_annual: float = 0.0       # 年干污泥量 (tDS/年)

    calculation_level: int = 0     # 数据完整性级别 (1–4)
    uncertainty_pct: float = 0.0   # 估算不确定性 (95% CI, %)
    warnings: List[str] = field(default_factory=list)
