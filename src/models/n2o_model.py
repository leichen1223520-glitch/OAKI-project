"""
M2：N₂O 排放子模型（双路径 DO 切换模型）

M2-nit：硝化 N₂O（路径A+B 合并，DO 依赖的 Michaelis-Menten 切换函数）
M2-denit：反硝化 N₂O（路径C，COD/TN 比修正函数）

创新点：
- 引入 DO 依赖的路径切换函数，区分"好氧区 DO 不足"与"缺碳反硝化不完全"
  两种 N₂O 升高机制，比单一排放因子法更精准
- DO_opt ≈ 2.0 mg/L 为 N₂O 最小点，低/高 DO 均可导致排放升高

参考文献：
- Ahn et al. (2010) Environ. Sci. Technol.
- Ribera-Guardia et al. (2014) Bioresour. Technol.
- Pijuan et al. (2014) Water Research
- Daelman et al. (2013) Water Research
"""
import numpy as np
from .params import ModelParams
from .inputs import ModelInput


class N2OModel:
    """
    M2：N₂O 双路径排放子模型

    L-Core 场景（无 DO 数据）：f_DO_nit = 1.0，附加 ±50% 不确定性
    L-Ext 场景（有月均 DO）：使用切换函数，不确定性降至 ±25%
    """

    def __init__(self, params: ModelParams):
        self.p = params

    # ─────────────────────────────────────────────────────────
    # 内部工具函数
    # ─────────────────────────────────────────────────────────

    def _f_DO_nit(self, DO: float) -> float:
        """
        DO 依赖的硝化 N₂O 路径切换函数（分段 Michaelis-Menten）。

        当 DO ≤ DO_opt（低 DO 区，路径B 激活）：
            f = 1 + (f_max - 1) × (DO_opt - DO) / (K_DO_high + DO_opt - DO)
        当 DO > DO_opt（高 DO 区，路径B 受抑）：
            f = 1 - f_decrease × (DO - DO_opt) / (K_DO_low + DO - DO_opt)

        返回值 ≥ 0
        """
        if DO is None:
            return 1.0  # L-Core 无 DO 时假设在最优点运行
        if DO <= self.p.DO_opt:
            delta = self.p.DO_opt - DO
            f = 1.0 + (self.p.f_max - 1.0) * delta / (self.p.K_DO_high + delta)
        else:
            delta = DO - self.p.DO_opt
            f = 1.0 - self.p.f_decrease * delta / (self.p.K_DO_low + delta)
        return max(0.0, f)

    def _g_CN(self, COD_TN: float) -> float:
        """
        COD/TN 比对反硝化 N₂O 排放因子的修正函数（指数衰减型）。

        当 COD/TN >> CN_crit：g → EF_denit_ref（碳源充足，N₂O 最低）
        当 COD/TN << CN_crit：g → EF_denit_ref × (1 + k_g)（碳源不足，N₂O 最高）
        """
        exponent = -(COD_TN - self.p.CN_crit) / self.p.k_CN
        # 限制指数范围防止溢出
        exponent = np.clip(exponent, -10.0, 10.0)
        g = self.p.EF_denit_ref * (1.0 + self.p.k_g * np.exp(exponent))
        return max(0.0, g)

    # ─────────────────────────────────────────────────────────
    # M2-nit：硝化 N₂O
    # ─────────────────────────────────────────────────────────

    def calculate_nit(self, inp: ModelInput) -> float:
        """
        计算硝化路径 N₂O 年排放量 (kgN₂O/年)

        核心方程：
        E_nit = ΔN_nit × EF_nit × f_DO × f_aq × (44/28)
        """
        # ── 年硝化氮量 (kgN/年) ──────────────────────────────
        dN_nit = (
            (inp.NH3N_in - inp.NH3N_out)
            * inp.Q_in * 365 * 1e-3  # mg/L × m³/d × d × 1e-3 → kgN/年
        )
        dN_nit = max(0.0, dN_nit)

        # ── DO 切换函数 ───────────────────────────────────────
        DO = inp.DO_aer  # None 时函数内部返回 1.0
        f_DO = self._f_DO_nit(DO)

        # ── N₂O 排放量 (kgN₂O/年) ────────────────────────────
        # EF_nit: kgN₂O-N/kgN，乘以 44/28 转为 kgN₂O
        e_nit = dN_nit * self.p.EF_nit * f_DO * self.p.f_aq * (44.0 / 28.0)
        return max(0.0, e_nit)

    # ─────────────────────────────────────────────────────────
    # M2-denit：反硝化 N₂O
    # ─────────────────────────────────────────────────────────

    def calculate_denit(self, inp: ModelInput) -> float:
        """
        计算反硝化路径 N₂O 年排放量 (kgN₂O/年)

        核心方程：
        E_denit = ΔN_denit × g(COD/TN) × f_aq × (44/28)
        """
        # ── 年总去氮量 (kgN/年) ──────────────────────────────
        dN_removed = (
            (inp.TN_in - inp.TN_out)
            * inp.Q_in * 365 * 1e-3
        )
        dN_removed = max(0.0, dN_removed)

        # ── 反硝化去氮量 ──────────────────────────────────────
        dN_denit = dN_removed * self.p.f_denit_fraction

        # ── COD/TN 比修正 ─────────────────────────────────────
        if inp.TN_in > 0:
            COD_TN = inp.COD_in / inp.TN_in
        else:
            COD_TN = self.p.CN_crit  # 无法计算时取临界值

        g = self._g_CN(COD_TN)

        # ── N₂O 排放量 (kgN₂O/年) ────────────────────────────
        e_denit = dN_denit * g * self.p.f_aq * (44.0 / 28.0)
        return max(0.0, e_denit)

    # ─────────────────────────────────────────────────────────
    # 汇总接口
    # ─────────────────────────────────────────────────────────

    def calculate(self, inp: ModelInput) -> float:
        """
        计算总 N₂O 年排放量 (kgN₂O/年)
        = M2-nit + M2-denit
        """
        return self.calculate_nit(inp) + self.calculate_denit(inp)

    def calculate_CO2eq(self, inp: ModelInput) -> float:
        """返回 N₂O 排放的 CO₂ 当量 (kgCO₂eq/年)"""
        return self.calculate(inp) * self.p.GWP_N2O
