"""
FPCM — Full-Plant Carbon emission Model
AAO 工艺污水处理厂全厂碳排放集成框架

架构：
  M1 (CH₄) + M2 (N₂O) → Scope 1 直接排放
  M3/M4 (能耗)         → Scope 2 电力间接排放
  M5 (药剂) + M6 (污泥) → Scope 3 其他间接排放

数据级别自适应（Level 1–4）：
  Level 1：仅 Q_in + E_total（其余用全国均值代替）        → 不确定性 ±52%
  Level 2：≥7 项 L-Core 参数                              → ±22%
  Level 3：完整 L-Core（10 项全有）                       → ±15%
  Level 4：L-Core + ≥3 项 L-Ext                          → ±10%

用法示例：
    from src.models.fpcm import FPCM
    from src.models.inputs import ModelInput

    inp = ModelInput(Q_in=50000, E_total_monthly=300000,
                     COD_in=300, TN_in=40, NH3N_in=30,
                     NH3N_out=1.5, TP_in=5, COD_out=30,
                     TN_out=10, T_water=22)
    result = FPCM().run(inp)
    print(f"全厂碳排放: {result.E_total_CO2eq/1e6:.3f} tCO₂eq/年")
    print(f"单位水量: {result.E_unit_kgCO2_m3:.4f} kgCO₂eq/m³")
"""
from __future__ import annotations
from typing import List

from .params import ModelParams
from .inputs import ModelInput, ModelOutput
from .ch4_model import CH4Model
from .n2o_model import N2OModel
from .energy_model import EnergyEmissionModel, AerationEnergyModel
from .chemical_model import ChemicalModel
from .sludge_model import SludgeDisposalModel

# 各级别不确定性估算（95% CI，%）
_UNCERTAINTY = {1: 52, 2: 22, 3: 15, 4: 10}

# 全国均值替代参数（Level 1 使用）
_NATIONAL_DEFAULTS = {
    "COD_in": 280.0,     # mg/L（Liu等,2022全国均值）
    "TN_in": 38.0,       # mg/L（Wang等,2021；与model_presets_v1全国均值一致）
    "NH3N_in": 27.0,     # mg/L（Wang等,2021全国均值）
    "NH3N_out": 5.0,
    "TP_in": 5.1,        # mg/L（Wang等,2021全国均值）
    "COD_out": 40.0,
    "TN_out": 12.0,
    "T_water": 18.0,
}


class FPCM:
    """
    全厂碳排放集成模型（FPCM v3.0）

    Parameters
    ----------
    params : ModelParams, optional
        模型参数（默认为先验均值）。
        贝叶斯率定后可传入后验均值或后验样本。
    """

    def __init__(self, params: ModelParams | None = None):
        self.params = params or ModelParams()
        self.M1 = CH4Model(self.params)
        self.M2 = N2OModel(self.params)
        self.M3 = AerationEnergyModel(self.params)
        self.energy = EnergyEmissionModel(self.params)
        self.M5 = ChemicalModel(self.params)
        self.M6 = SludgeDisposalModel(self.params)

    # ─────────────────────────────────────────────────────────
    # 数据质量评估
    # ─────────────────────────────────────────────────────────

    def _determine_level(self, inp: ModelInput) -> int:
        """确定数据完整性级别（1–4）"""
        core_fields = [
            inp.Q_in, inp.E_total_monthly, inp.COD_in,
            inp.TN_in, inp.NH3N_in, inp.NH3N_out,
            inp.TP_in, inp.COD_out, inp.TN_out,
        ]
        n_core = sum(1 for v in core_fields if v and v > 0)

        ext_fields = [
            inp.DO_aer, inp.MLSS, inp.SRT,
            inp.W_sludge, inp.PAC_monthly, inp.carbon_dose_monthly,
        ]
        n_ext = sum(1 for v in ext_fields if v is not None)

        if n_core >= 9 and n_ext >= 3:
            return 4
        elif n_core >= 9:
            return 3
        elif n_core >= 7:
            return 2
        else:
            return 1

    def _validate_inputs(self, inp: ModelInput) -> List[str]:
        """基本物理合理性检查，返回警告列表"""
        warnings = []
        if inp.Q_in <= 0:
            warnings.append("Q_in ≤ 0，请检查进水量单位（应为 m³/d）")
        if inp.E_total_monthly <= 0:
            warnings.append("E_total_monthly ≤ 0，请检查月电耗数据")
        if inp.COD_in > 0 and inp.COD_out > inp.COD_in:
            warnings.append("COD_out > COD_in，出水 COD 不应高于进水")
        if inp.TN_in > 0 and inp.TN_out > inp.TN_in:
            warnings.append("TN_out > TN_in，出水 TN 不应高于进水")
        if inp.T_water < 5 or inp.T_water > 40:
            warnings.append(f"T_water={inp.T_water}°C 超出正常运行范围（5–40°C）")
        return warnings

    def _impute_missing(self, inp: ModelInput, level: int) -> ModelInput:
        """Level 1 时用全国均值填充缺失字段"""
        if level > 1:
            return inp
        import copy
        inp2 = copy.copy(inp)
        for field, default in _NATIONAL_DEFAULTS.items():
            if getattr(inp2, field, None) in (None, 0.0):
                setattr(inp2, field, default)
        return inp2

    # ─────────────────────────────────────────────────────────
    # 核心计算
    # ─────────────────────────────────────────────────────────

    def run(self, inp: ModelInput, validate: bool = True) -> ModelOutput:
        """
        运行 FPCM，返回完整碳排放结果。

        Parameters
        ----------
        inp : ModelInput
            单次（月度或年度代表值）输入数据
        validate : bool
            是否进行输入合理性检查

        Returns
        -------
        ModelOutput
            包含 Scope 1/2/3 拆分、单位排放、级别和不确定性
        """
        out = ModelOutput()

        # Step 0: 数据验证
        if validate:
            out.warnings = self._validate_inputs(inp)

        # Step 1: 确定计算级别 & 缺失值填充
        level = self._determine_level(inp)
        inp = self._impute_missing(inp, level)
        out.calculation_level = level
        out.uncertainty_pct = _UNCERTAINTY.get(level, 52)

        # ── Scope 1：直接温室气体排放 ────────────────────────
        e_ch4_kg = self.M1.calculate(inp)           # kgCH₄/年
        e_n2o_kg = self.M2.calculate(inp)           # kgN₂O/年

        out.E_CH4_kg = e_ch4_kg
        out.E_N2O_kg = e_n2o_kg
        out.E_N2O_nit = self.M2.calculate_nit(inp)
        out.E_N2O_denit = self.M2.calculate_denit(inp)
        out.E_Scope1_CO2eq = (
            e_ch4_kg * self.params.GWP_CH4
            + e_n2o_kg * self.params.GWP_N2O
        )
        out.TOW = self.M1.get_TOW(inp)

        # ── Scope 2：电力间接排放 ─────────────────────────────
        e_total_kwh = inp.E_total_monthly * 12.0
        out.E_total_kWh = e_total_kwh
        out.E_Scope2_CO2eq = self.energy.calculate_CO2eq(inp)
        out.E_aer_CO2eq = (
            self.M3.calculate_kwh(inp) * self.params.EF_grid
        )

        # ── Scope 3：其他间接排放 ─────────────────────────────
        e_chem = self.M5.calculate(inp)
        e_sludge = self.M6.calculate(inp)
        out.E_chem_CO2eq = e_chem
        out.E_sludge_CO2eq = e_sludge
        out.E_Scope3_CO2eq = e_chem + e_sludge
        out.W_DS_annual = self.M6.get_annual_DS(inp)

        # ── 汇总 ────────────────────────────────────────────
        out.E_total_CO2eq = (
            out.E_Scope1_CO2eq
            + out.E_Scope2_CO2eq
            + out.E_Scope3_CO2eq
        )

        # 单位水量碳排放 (kgCO₂eq/m³)
        annual_volume = inp.Q_in * 365.0  # m³/年
        if annual_volume > 0:
            out.E_unit_kgCO2_m3 = out.E_total_CO2eq / annual_volume
        else:
            out.E_unit_kgCO2_m3 = 0.0

        return out

    def summary(self, out: ModelOutput) -> str:
        """格式化打印结果摘要"""
        lines = [
            "=" * 55,
            "  FPCM v3.0 — 全厂碳排放计算结果",
            "=" * 55,
            f"  数据级别：Level {out.calculation_level}  "
            f"（不确定性 ±{out.uncertainty_pct}%）",
            "-" * 55,
            "  Scope 1 直接排放",
            f"    CH₄: {out.E_CH4_kg:,.1f} kgCH₄/年  "
            f"= {out.E_CH4_kg*self.params.GWP_CH4/1e3:,.1f} tCO₂eq",
            f"    N₂O: {out.E_N2O_kg:,.1f} kgN₂O/年  "
            f"= {out.E_N2O_kg*self.params.GWP_N2O/1e3:,.1f} tCO₂eq",
            f"    Scope 1 合计: {out.E_Scope1_CO2eq/1e3:,.1f} tCO₂eq/年",
            "-" * 55,
            "  Scope 2 电力间接排放",
            f"    年电耗: {out.E_total_kWh:,.0f} kWh",
            f"    Scope 2 合计: {out.E_Scope2_CO2eq/1e3:,.1f} tCO₂eq/年",
            "-" * 55,
            "  Scope 3 其他间接排放",
            f"    药剂: {out.E_chem_CO2eq/1e3:,.1f} tCO₂eq/年",
            f"    污泥处置: {out.E_sludge_CO2eq/1e3:,.1f} tCO₂eq/年  "
            f"（{out.W_DS_annual:,.1f} tDS）",
            f"    Scope 3 合计: {out.E_Scope3_CO2eq/1e3:,.1f} tCO₂eq/年",
            "=" * 55,
            f"  全厂总排放: {out.E_total_CO2eq/1e3:,.1f} tCO₂eq/年",
            f"  单位水量:   {out.E_unit_kgCO2_m3:.4f} kgCO₂eq/m³",
        ]
        if out.warnings:
            lines.append("-" * 55)
            lines.append("  ⚠ 数据质量警告：")
            for w in out.warnings:
                lines.append(f"    · {w}")
        lines.append("=" * 55)
        return "\n".join(lines)
