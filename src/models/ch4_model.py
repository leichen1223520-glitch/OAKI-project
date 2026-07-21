"""
M1：CH₄ 排放子模型
基于 IPCC Tier 2 框架 + Arrhenius 温度修正 + 贝叶斯先验参数化

核心方程：
E_CH4 = TOW_avail × MCF × B0 × f_T × (1 - f_rec) × GWP_CH4

参考文献：
- Daelman et al. (2012) Water Research
- IPCC (2019) Wastewater Treatment Chapter
- Metcalf & Eddy (2014) Wastewater Engineering
"""
import numpy as np
from .params import ModelParams
from .inputs import ModelInput


class CH4Model:
    """
    M1：CH₄ 排放子模型

    适用条件：
    - 纯好氧活性污泥系统（AAO 工艺）
    - 无配套厌氧消化（f_rec=0），若有则需修正
    - 进水工业废水比例 < 30%（COD/BOD < 2.5）
    """

    def __init__(self, params: ModelParams):
        self.p = params

    def calculate(self, inp: ModelInput) -> float:
        """
        计算年 CH₄ 排放量。

        Parameters
        ----------
        inp : ModelInput
            包含 Q_in, COD_in, T_water

        Returns
        -------
        e_ch4_kg : float
            年 CH₄ 排放量 (kgCH₄/年)
        """
        # ── 步骤1：年 TOW（以 BOD 计，tBOD/年）──────────────
        BOD_in = self.p.f_boc * inp.COD_in          # mg/L BOD
        TOW = (inp.Q_in * BOD_in * 365 * 1e-6)       # tBOD/年

        # ── 步骤2：扣除随污泥去除的有机物 ───────────────────
        TOW_avail = TOW * (1.0 - self.p.f_sludge_org)

        # ── 步骤3：温度修正（改进型 Arrhenius）──────────────
        f_T = self.p.theta_T ** (inp.T_water - self.p.T_ref)

        # ── 步骤4：CH₄ 排放量（kgCH₄/年）───────────────────
        # TOW_avail (tBOD/年) × MCF × B0 (kgCH4/kgBOD) × f_T × (1-f_rec)
        # × 1000 将 t → kg
        e_ch4_kg = (
            TOW_avail * 1000.0
            * self.p.MCF
            * self.p.B0
            * f_T
            * (1.0 - self.p.f_rec)
        )

        return max(0.0, e_ch4_kg)

    def calculate_CO2eq(self, inp: ModelInput) -> float:
        """返回 CH₄ 排放的 CO₂ 当量 (kgCO₂eq/年)"""
        return self.calculate(inp) * self.p.GWP_CH4

    def get_TOW(self, inp: ModelInput) -> float:
        """返回总有机物投入 (tBOD/年)，供集成框架调用"""
        return inp.Q_in * self.p.f_boc * inp.COD_in * 365 * 1e-6
