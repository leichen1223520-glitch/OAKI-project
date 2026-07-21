"""
FPCM 模型参数定义
包含所有子模型的先验默认值，可通过贝叶斯率定更新。
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelParams:
    """
    全厂碳排放模型（FPCM）所有可率定参数的容器。
    默认值为第四章表4-4中的先验均值。
    """
    # ── M1：CH₄ 参数 ──────────────────────────────────────────
    f_boc: float = 0.48        # BOD/COD 比值
    f_sludge_org: float = 0.25 # 污泥有机碳占进水BOD比例（由Y_obs推算）
    MCF: float = 0.028         # 甲烷修正因子
    B0: float = 0.60           # 最大甲烷产生潜力（kgCH₄/kgBOD）
    theta_T: float = 1.040     # Arrhenius温度修正基数
    T_ref: float = 20.0        # 参考温度 (°C)
    f_rec: float = 0.0         # CH₄回收利用率（无厌氧消化时=0）
    GWP_CH4: float = 28.0      # IPCC AR5 甲烷增温潜势

    # ── M2：N₂O 参数 ─────────────────────────────────────────
    EF_nit: float = 0.0035     # 硝化N₂O排放因子 (kgN₂O-N/kgN_nitrified)
    DO_opt: float = 2.0        # 最优DO (mg/L)，N₂O排放最小处
    f_max: float = 3.0         # 低DO时N₂O增强因子上限
    K_DO_high: float = 0.8     # Michaelis常数（低DO侧，mg/L）
    K_DO_low: float = 1.5      # Michaelis常数（高DO侧，mg/L）
    f_decrease: float = 0.3    # 高DO时N₂O减少系数
    f_aq: float = 1.20         # 出水溶解N₂O修正系数

    EF_denit_ref: float = 0.0012   # 反硝化参考排放因子 (kgN₂O-N/kgN_denit)
    CN_crit: float = 6.5           # 临界 COD/TN 比
    k_g: float = 2.0               # C/N不足时N₂O增强倍数
    k_CN: float = 1.5              # C/N修正过渡宽度参数（固定）
    f_denit_fraction: float = 0.85 # 反硝化占总去氮比例

    GWP_N2O: float = 265.0     # IPCC AR5 N₂O增温潜势

    # ── M3/M4：能耗参数 ──────────────────────────────────────
    alpha: float = 0.65        # 污水传质修正系数
    F_fouling: float = 0.87    # 积垢/堵塞修正系数
    beta: float = 0.95         # 盐度修正系数
    DO_aer: float = 2.0        # 好氧区溶解氧设定值 (mg/L)
    SOTE: float = 0.20         # 标准条件氧转移效率
    eta_blower: float = 0.70   # 鼓风机效率

    r_aer: float = 0.576       # 曝气电耗分配比（无AOR数据时用）
    r_pump: float = 0.183      # 水泵电耗分配比
    r_sludge: float = 0.10     # 污泥处理电耗分配比

    EF_grid: float = 0.5839    # 电网排放因子 (kgCO₂/kWh)，全国均值2022年

    # ── M5：药剂参数 ─────────────────────────────────────────
    EF_PAC: float = 1.60       # PAC Cradle-to-Gate 碳排放因子 (kgCO₂eq/kg)
    EF_carbon_source: float = 0.90  # 外加碳源（甲醇/乙酸钠）排放因子 (kgCO₂eq/kg)
    EF_disinfect: float = 0.70      # 消毒剂排放因子 (kgCO₂eq/kg)
    r_Al_extra: float = 1.8    # PAC实际/理论投加比
    CN_target: float = 5.5     # 反硝化安全碳源投加目标C/N比
    eta_carbon: float = 0.85   # 外加碳源利用效率

    # ── M6：污泥参数 ─────────────────────────────────────────
    Y_obs: float = 0.42        # 表观产泥系数 (kgVSS/kgBOD)
    MC_sludge: float = 0.80    # 脱水后污泥含水率
    # 处置方式碳排放因子 (kgCO₂eq/tDS)，默认：好氧堆肥（封闭）
    EF_disposal: float = 360.0
