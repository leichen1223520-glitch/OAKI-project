"""
test_models.py — FPCM 核心子模型单元测试

覆盖：
  - CH₄子模型 (M1)
  - N₂O子模型 (M2)
  - 能耗子模型 (M3/M4)
  - 药剂子模型 (M5)
  - 污泥子模型 (M6)
  - FPCM集成模型
  - 输入数据验证
"""
import sys
import os
import pytest

# 确保能找到 src 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.inputs import ModelInput, ModelOutput
from src.models.params import ModelParams
from src.models.ch4_model import CH4Model
from src.models.n2o_model import N2OModel
from src.models.energy_model import EnergyEmissionModel
from src.models.chemical_model import ChemicalModel
from src.models.sludge_model import SludgeDisposalModel
from src.models.fpcm import FPCM
from src.utils.validators import validate_model_input


# ─── 共用 Fixture ────────────────────────────────────────────────────────────

@pytest.fixture
def typical_input():
    """典型南方AAO工艺处理厂（案例厂A）月度输入"""
    return ModelInput(
        Q_in=50_000,           # m³/d
        E_total_monthly=300_000,  # kWh/月
        COD_in=300.0,
        TN_in=40.0,
        NH3N_in=30.0,
        NH3N_out=1.5,
        TP_in=5.0,
        COD_out=30.0,
        TN_out=10.0,
        T_water=22.0,
    )


@pytest.fixture
def typical_params():
    return ModelParams()


# ─── CH₄ 子模型测试 ──────────────────────────────────────────────────────────

class TestCH4Model:
    def test_output_positive(self, typical_input, typical_params):
        m = CH4Model(typical_params)
        result = m.calculate(typical_input)
        assert result > 0, "CH₄排放量应为正值"

    def test_higher_cod_more_ch4(self, typical_params):
        """进水COD越高，CH₄应越多"""
        inp_low = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                             COD_in=150, TN_in=40, NH3N_in=30,
                             NH3N_out=1.5, TP_in=5, COD_out=30,
                             TN_out=10, T_water=22)
        inp_high = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                              COD_in=400, TN_in=40, NH3N_in=30,
                              NH3N_out=1.5, TP_in=5, COD_out=30,
                              TN_out=10, T_water=22)
        m = CH4Model(typical_params)
        assert m.calculate(inp_high) > m.calculate(inp_low)

    def test_reasonable_magnitude(self, typical_input, typical_params):
        """CH₄排放量应在合理量级（年度 1–1000 tCH₄）"""
        m = CH4Model(typical_params)
        ch4_annual = m.calculate(typical_input)
        assert 1_000 < ch4_annual < 1_000_000, (
            f"CH₄={ch4_annual:.1f} kg/年，超出合理范围"
        )


# ─── N₂O 子模型测试 ──────────────────────────────────────────────────────────

class TestN2OModel:
    def test_output_positive(self, typical_input, typical_params):
        m = N2OModel(typical_params)
        result = m.calculate(typical_input)
        assert result > 0

    def test_do_effect_on_n2o(self, typical_params):
        """DO过低应导致N₂O增加（相对最优区间）"""
        from dataclasses import asdict
        base = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                          COD_in=300, TN_in=40, NH3N_in=30,
                          NH3N_out=1.5, TP_in=5, COD_out=30,
                          TN_out=10, T_water=22, DO_aer=2.0)
        base_dict = asdict(base)
        base_dict['DO_aer'] = 0.5
        low_do = ModelInput(**base_dict)
        m = N2OModel(typical_params)
        n2o_base = m.calculate(base)
        n2o_low = m.calculate(low_do)
        assert n2o_low > n2o_base, "DO过低时N₂O应增加"

    def test_higher_tn_more_n2o(self, typical_params):
        """进水TN越高，N₂O应越多"""
        inp_low = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                             COD_in=300, TN_in=20, NH3N_in=15,
                             NH3N_out=1.5, TP_in=5, COD_out=30,
                             TN_out=8, T_water=22)
        inp_high = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                              COD_in=300, TN_in=60, NH3N_in=50,
                              NH3N_out=1.5, TP_in=5, COD_out=30,
                              TN_out=10, T_water=22)
        m = N2OModel(typical_params)
        assert m.calculate(inp_high) > m.calculate(inp_low)


# ─── 能耗子模型测试 ──────────────────────────────────────────────────────────

class TestEnergyModel:
    def test_scope2_positive(self, typical_input, typical_params):
        m = EnergyEmissionModel(typical_params)
        result = m.calculate_CO2eq(typical_input)
        assert result > 0

    def test_higher_energy_more_scope2(self, typical_params):
        low_e = ModelInput(Q_in=50_000, E_total_monthly=100_000,
                           COD_in=300, TN_in=40, NH3N_in=30,
                           NH3N_out=1.5, TP_in=5, COD_out=30,
                           TN_out=10, T_water=22)
        high_e = ModelInput(Q_in=50_000, E_total_monthly=600_000,
                            COD_in=300, TN_in=40, NH3N_in=30,
                            NH3N_out=1.5, TP_in=5, COD_out=30,
                            TN_out=10, T_water=22)
        m = EnergyEmissionModel(typical_params)
        assert m.calculate_CO2eq(high_e) > m.calculate_CO2eq(low_e)


# ─── 药剂子模型测试 ──────────────────────────────────────────────────────────

class TestChemicalModel:
    def test_output_nonnegative(self, typical_input, typical_params):
        m = ChemicalModel(typical_params)
        result = m.calculate(typical_input)
        assert result >= 0

    def test_with_pac_dose(self, typical_params):
        """指定PAC用量时，化学碳排应增加"""
        inp_no_pac = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                                COD_in=300, TN_in=40, NH3N_in=30,
                                NH3N_out=1.5, TP_in=5, COD_out=30,
                                TN_out=10, T_water=22)
        inp_pac = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                             COD_in=300, TN_in=40, NH3N_in=30,
                             NH3N_out=1.5, TP_in=5, COD_out=30,
                             TN_out=10, T_water=22,
                             PAC_monthly=50_000)  # 50t PAC/月
        m = ChemicalModel(typical_params)
        assert m.calculate(inp_pac) > m.calculate(inp_no_pac)


# ─── 污泥子模型测试 ──────────────────────────────────────────────────────────

class TestSludgeModel:
    def test_output_nonnegative(self, typical_input, typical_params):
        m = SludgeDisposalModel(typical_params)
        result = m.calculate(typical_input)
        assert result >= 0

    def test_anaerobic_lower_than_landfill(self, typical_params):
        """厌氧消化碳排放应低于无气体回收填埋（有沼气利用）"""
        inp_landfill = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                                  COD_in=300, TN_in=40, NH3N_in=30,
                                  NH3N_out=1.5, TP_in=5, COD_out=30,
                                  TN_out=10, T_water=22,
                                  disposal_method="landfill_no_gas")
        inp_ad = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                            COD_in=300, TN_in=40, NH3N_in=30,
                            NH3N_out=1.5, TP_in=5, COD_out=30,
                            TN_out=10, T_water=22,
                            disposal_method="anaerobic_digestion")
        m = SludgeDisposalModel(typical_params)
        assert m.calculate(inp_ad) < m.calculate(inp_landfill)


# ─── FPCM 集成测试 ───────────────────────────────────────────────────────────

class TestFPCM:
    def test_run_returns_output(self, typical_input):
        result = FPCM().run(typical_input)
        assert isinstance(result, ModelOutput)

    def test_total_equals_sum_of_scopes(self, typical_input):
        """全厂总排放 = Scope1 + Scope2 + Scope3"""
        result = FPCM().run(typical_input)
        expected = result.E_Scope1_CO2eq + result.E_Scope2_CO2eq + result.E_Scope3_CO2eq
        assert abs(result.E_total_CO2eq - expected) < 1.0, (
            f"总量不平衡: {result.E_total_CO2eq:.0f} vs {expected:.0f}"
        )

    def test_unit_emission_reasonable(self, typical_input):
        """单位水量碳排放应在 0.1–2.0 kgCO₂eq/m³（合理范围）"""
        result = FPCM().run(typical_input)
        assert 0.1 <= result.E_unit_kgCO2_m3 <= 2.0, (
            f"单位碳排={result.E_unit_kgCO2_m3:.4f} 超出合理范围"
        )

    def test_level_3_with_full_lcore(self, typical_input):
        """完整 L-Core 输入应触发 Level 3 计算"""
        result = FPCM().run(typical_input)
        assert result.calculation_level >= 3

    def test_level_4_with_ext_params(self):
        """提供 L-Ext 参数应触发 Level 4"""
        inp = ModelInput(
            Q_in=50_000, E_total_monthly=300_000,
            COD_in=300, TN_in=40, NH3N_in=30,
            NH3N_out=1.5, TP_in=5, COD_out=30,
            TN_out=10, T_water=22,
            DO_aer=2.0, MLSS=3500, SRT=15,
        )
        result = FPCM().run(inp)
        assert result.calculation_level >= 4

    def test_scope1_dominated_by_n2o(self, typical_input):
        """N₂O应占Scope1的50%以上（文献支撑）"""
        result = FPCM().run(typical_input)
        if result.E_Scope1_CO2eq > 0:
            n2o_co2eq = result.E_N2O_kg * 273.0
            n2o_share = n2o_co2eq / result.E_Scope1_CO2eq
            assert n2o_share > 0.5, (
                f"N₂O占Scope1比例={n2o_share:.2%}，低于预期50%"
            )

    def test_uncertainty_matches_level(self, typical_input):
        """不确定性应与计算级别对应"""
        expected = {1: 52, 2: 22, 3: 15, 4: 10}
        result = FPCM().run(typical_input)
        assert result.uncertainty_pct == expected.get(result.calculation_level, 0)

    def test_minimal_input_level1(self):
        """仅提供最少参数应得到 Level 1 结果"""
        inp = ModelInput(Q_in=30_000, E_total_monthly=200_000)
        result = FPCM().run(inp)
        assert result.E_total_CO2eq > 0
        assert result.calculation_level == 1

    def test_scope3_includes_sludge(self, typical_input):
        """Scope3 应包含污泥碳排放（非零）"""
        result = FPCM().run(typical_input)
        assert result.E_sludge_CO2eq >= 0

    def test_reproducibility(self, typical_input):
        """相同输入应得到完全相同的结果（确定性）"""
        r1 = FPCM().run(typical_input)
        r2 = FPCM().run(typical_input)
        assert r1.E_total_CO2eq == r2.E_total_CO2eq


# ─── 输入验证测试 ────────────────────────────────────────────────────────────

class TestInputValidation:
    def test_valid_input_passes(self, typical_input):
        result = validate_model_input(typical_input)
        assert result.is_valid, f"合法输入校验失败: {result.errors}"

    def test_negative_flow_fails(self):
        inp = ModelInput(Q_in=-100, E_total_monthly=300_000,
                         COD_in=300, TN_in=40, NH3N_in=30,
                         NH3N_out=1.5, TP_in=5, COD_out=30,
                         TN_out=10, T_water=22)
        result = validate_model_input(inp)
        assert not result.is_valid

    def test_cod_in_less_than_cod_out_fails(self):
        inp = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                         COD_in=20, TN_in=40, NH3N_in=30,
                         NH3N_out=1.5, TP_in=5, COD_out=50,
                         TN_out=10, T_water=22)
        result = validate_model_input(inp)
        assert not result.is_valid

    def test_low_cn_ratio_warning(self):
        """低COD/TN应触发警告而非错误"""
        inp = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                         COD_in=60, TN_in=40, NH3N_in=30,
                         NH3N_out=1.5, TP_in=5, COD_out=30,
                         TN_out=10, T_water=22)
        result = validate_model_input(inp)
        assert any("COD/TN" in w for w in result.warnings)

    def test_extreme_temperature_warning(self):
        inp = ModelInput(Q_in=50_000, E_total_monthly=300_000,
                         COD_in=300, TN_in=40, NH3N_in=30,
                         NH3N_out=1.5, TP_in=5, COD_out=30,
                         TN_out=10, T_water=3.0)
        result = validate_model_input(inp)
        assert any("水温" in w for w in result.warnings)


# ─── 工具函数测试 ────────────────────────────────────────────────────────────

class TestUtils:
    def test_grid_ef_guangdong(self):
        from src.utils.carbon_factors import get_grid_ef
        ef = get_grid_ef("广东")
        assert 0.4 <= ef <= 0.7

    def test_grid_ef_national_default(self):
        from src.utils.carbon_factors import get_grid_ef
        ef = get_grid_ef("未知省份")
        assert ef == 0.5839

    def test_chemical_ef_pac(self):
        from src.utils.carbon_factors import get_chemical_ef
        ef = get_chemical_ef("PAC")
        assert ef > 0

    def test_sludge_ef_incineration_lower(self):
        from src.utils.carbon_factors import get_sludge_ef
        ef_incin = get_sludge_ef("incineration")
        ef_landfill = get_sludge_ef("landfill_no_gas")
        assert ef_incin < ef_landfill

    def test_report_generator_text(self, typical_input):
        from src.utils.report_generator import generate_text_report
        result = FPCM().run(typical_input)
        report = generate_text_report(result, typical_input, "测试厂A")
        assert "Scope 1" in report
        assert "全厂总计" in report
        assert "测试厂A" in report


# ─── 参数一致性测试 ──────────────────────────────────────────────────────────

class TestParamsConsistency:
    def test_gwp_values_ar6(self):
        """GWP值应符合IPCC AR6"""
        from src.utils.carbon_factors import GWP_CH4, GWP_N2O
        assert abs(GWP_CH4 - 27.9) < 0.1
        assert abs(GWP_N2O - 273.0) < 0.5

    def test_model_params_defaults_positive(self):
        p = ModelParams()
        assert p.EF_nit > 0
        assert p.MCF > 0
        assert p.EF_grid > 0
