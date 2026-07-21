"""
M5：药剂投加碳排放子模型

接口：
1. 有台账时（PAC_monthly / carbon_dose_monthly 已知）：直接计算
2. 无台账时（仅有进水 TP / TN / COD）：通过化学计量估算投加量

PAC 化学除磷估算基于 Al:P 摩尔比 1.5:1
外加碳源估算基于目标 C/N 比 5.5

排放因子来源（Cradle-to-Gate）：
- PAC：1.60 kgCO₂eq/kg
- 甲醇/乙酸钠：0.90 kgCO₂eq/kg
- 消毒剂：0.70 kgCO₂eq/kg

参考文献：
- Henze et al. (2000) 生物除磷模型
- 表2-4 Cradle-to-Gate LCA 因子汇总
"""
import numpy as np
from .params import ModelParams
from .inputs import ModelInput

# PAC：Al₂(SO₄)₃·18H₂O 或 Al₂(OH)₃Cl₃，Al 质量分数约 15.6%
PAC_Al_FRACTION = 0.156
# Al 摩尔质量 (g/mol)
MW_AL = 26.98
# P 摩尔质量 (g/mol)
MW_P = 30.97
# 化学计量 Al:P 摩尔比
AL_P_MOLAR_RATIO = 1.5


class ChemicalModel:
    """
    M5：药剂投加碳排放子模型
    """

    def __init__(self, params: ModelParams):
        self.p = params

    # ─────────────────────────────────────────────────────────
    # 台账接口
    # ─────────────────────────────────────────────────────────

    def _from_ledger(self, inp: ModelInput) -> float:
        """
        有台账时（月用量已知）直接计算年药剂碳排放 (kgCO₂eq/年)
        """
        E = 0.0

        if inp.PAC_monthly is not None:
            E += inp.PAC_monthly * 12.0 * self.p.EF_PAC

        if inp.carbon_dose_monthly is not None:
            E += inp.carbon_dose_monthly * 12.0 * self.p.EF_carbon_source

        return E

    # ─────────────────────────────────────────────────────────
    # 无台账工程估算
    # ─────────────────────────────────────────────────────────

    def _estimate_PAC(self, inp: ModelInput) -> float:
        """
        化学计量法估算年 PAC 用量 (kg/年)

        m_PAC = (ΔP_chem × Q × 365 × 1e-3) / PAC_Al_fraction × r_Al_extra
        其中 ΔP_chem = max(0, TP_in - TP_bio - TP_out)
        TP_bio ≈ 0.015 × MLSS（mg P/L）
        """
        TP_bio = 0.015 * (inp.MLSS if inp.MLSS is not None else 3000.0)
        dP_chem = max(0.0, inp.TP_in - TP_bio - 0.5)  # 0.5 mg/L 出水 TP 目标

        # 理论 Al 需求 (g/L)
        Al_theory = dP_chem * (AL_P_MOLAR_RATIO * MW_AL / MW_P)
        # PAC 理论投加量 (mg/L)
        PAC_theory = Al_theory / PAC_Al_FRACTION

        # 年 PAC 量 (kg/年)，含过量系数
        m_PAC = (
            PAC_theory * inp.Q_in * 365 * 1e-6 * 1000.0
            * self.p.r_Al_extra
        )
        return max(0.0, m_PAC)

    def _estimate_carbon_source(self, inp: ModelInput) -> float:
        """
        工程估算法：COD/TN < 5 时估算需补充的外加碳源年用量 (kg/年)

        m_carbon = Q × TN_denit × (CN_target - COD/TN) / eta_carbon × 365 × 1e-3
        """
        if inp.TN_in <= 0:
            return 0.0
        COD_TN = inp.COD_in / inp.TN_in

        if COD_TN >= 5.0:
            return 0.0  # 碳源充足，无需补充

        # 需反硝化的 TN 量 (mg/L)
        TN_denit = (inp.TN_in - inp.TN_out) * self.p.f_denit_fraction

        deficit_CN = max(0.0, self.p.CN_target - COD_TN)

        m_carbon = (
            inp.Q_in * TN_denit * deficit_CN
            / self.p.eta_carbon
            * 365 * 1e-6 * 1000.0  # mg/L × m³/d → kg/年
        )
        return max(0.0, m_carbon)

    # ─────────────────────────────────────────────────────────
    # 主接口
    # ─────────────────────────────────────────────────────────

    def calculate(self, inp: ModelInput) -> float:
        """
        计算年药剂投加碳排放 (kgCO₂eq/年)

        优先使用台账数据；若无台账则用工程估算。
        """
        has_ledger = (
            inp.PAC_monthly is not None
            or inp.carbon_dose_monthly is not None
        )

        if has_ledger:
            return self._from_ledger(inp)

        # 无台账：工程估算
        m_PAC = self._estimate_PAC(inp)
        m_carbon = self._estimate_carbon_source(inp)

        E_chem = m_PAC * self.p.EF_PAC + m_carbon * self.p.EF_carbon_source
        return max(0.0, E_chem)
