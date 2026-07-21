"""
M3 + M4：能耗碳排放子模型

M3：曝气能耗
  - 正向AOR法（L-Core完整时，通过需氧量计算）
  - 反查分配系数法（仅有E_total时）

M4：其他能耗（水泵、污泥处理、辅助设备）
  - 均通过电耗分配系数估算

间接碳排放：E_elec_CO2eq = E_total × EF_grid

参考文献：
- Tchobanoglous et al. (2014) Wastewater Engineering
- Metcalf & Eddy (2014) 第7章
- Yang et al. (2020) 国内15座AAO厂实测调研
- 生态环境部 (2023) 省级电网排放因子
"""
import numpy as np
from .params import ModelParams
from .inputs import ModelInput

# 清水20°C饱和 DO (mg/L)
Cs_20 = 9.08


class AerationEnergyModel:
    """
    M3：曝气能耗子模型

    当 COD_in > 0 且 COD_out >= 0 时使用正向 AOR 法；
    否则使用分配系数反查法。
    """

    def __init__(self, params: ModelParams):
        self.p = params

    def _calc_AOR(self, inp: ModelInput) -> float:
        """
        正向需氧量计算（kgO₂/d）

        AOR = AOR_carbon + AOR_nitrification - AOR_denitrification
        """
        Q = inp.Q_in  # m³/d

        # 碳化耗氧系数 a_org
        a_org = 1.0 - 1.42 * self.p.Y_obs / self.p.f_boc
        a_org = max(0.3, min(a_org, 0.9))  # 物理合理范围

        # 碳化需氧量 (kgO₂/d)
        AOR_carbon = Q * (inp.COD_in - inp.COD_out) * a_org * 1e-3

        # 硝化需氧量 (kgO₂/d)  4.33 gO₂/gNH4-N
        AOR_nit = 4.33 * Q * (inp.NH3N_in - inp.NH3N_out) * 1e-3
        AOR_nit = max(0.0, AOR_nit)

        # 反硝化还氧量 (kgO₂/d)  2.86 gO₂/gNO3-N
        dN_denit = max(0.0, inp.TN_in - inp.TN_out) * self.p.f_denit_fraction
        AOR_denit = 2.86 * Q * dN_denit * 1e-3
        AOR_denit = max(0.0, AOR_denit)

        AOR = AOR_carbon + AOR_nit - AOR_denit
        return max(0.0, AOR)

    def _AOR_to_power(self, AOR: float, T: float, DO_set: float) -> float:
        """
        AOR (kgO₂/d) → 鼓风机轴功率 (kW)

        P = SOR × 1000 / (SOTE × eta × rho_air × 0.232)
        其中 SOR = AOR × Cs20 / (α × F × (β × CsT - CL))
        """
        # 温度修正后饱和 DO (mg/L)：van't Hoff近似
        Cs_T = Cs_20 * np.exp(-0.0223 * (T - 20.0))
        Cs_T = max(1.0, Cs_T)

        denominator = self.p.alpha * self.p.F_fouling * (
            self.p.beta * Cs_T - DO_set
        )
        if denominator <= 0:
            denominator = 1.0  # 防止除零

        SOR = AOR * Cs_20 / denominator  # kgO₂/d

        # 鼓风机功率 (kW)
        rho_air = 1.225  # kg/m³，标准状态
        P = (SOR * 1000.0) / (
            self.p.SOTE * self.p.eta_blower * rho_air * 0.232 * 86400.0
        )
        return max(0.0, P)

    def calculate_kwh(self, inp: ModelInput) -> float:
        """
        计算年曝气电耗 (kWh/年)。
        优先使用 AOR 法，数据不足时使用分配系数法。
        """
        use_AOR = (
            inp.COD_in > 0
            and inp.COD_out >= 0
            and inp.NH3N_in > 0
        )

        if use_AOR:
            AOR = self._calc_AOR(inp)
            DO_set = inp.DO_aer if inp.DO_aer is not None else self.p.DO_aer
            P_kW = self._AOR_to_power(AOR, inp.T_water, DO_set)
            E_aer = P_kW * 8760.0  # kWh/年
        else:
            # 分配系数反查法
            E_total_annual = inp.E_total_monthly * 12.0
            E_aer = E_total_annual * self.p.r_aer

        return max(0.0, E_aer)


class OtherEnergyModel:
    """
    M4：其他能耗子模型（水泵、污泥处理、辅助设备）
    均通过电耗分配系数估算。
    """

    def __init__(self, params: ModelParams):
        self.p = params

    def calculate_breakdown(self, inp: ModelInput) -> dict:
        """
        返回各子系统年电耗分配（kWh/年）
        """
        E_annual = inp.E_total_monthly * 12.0
        E_pump = E_annual * self.p.r_pump
        E_sludge_proc = E_annual * self.p.r_sludge
        E_aer = E_annual * self.p.r_aer
        E_misc = E_annual - E_aer - E_pump - E_sludge_proc
        E_misc = max(0.0, E_misc)
        return {
            "E_aer": E_aer,
            "E_pump": E_pump,
            "E_sludge_proc": E_sludge_proc,
            "E_misc": E_misc,
            "E_total": E_annual,
        }


class EnergyEmissionModel:
    """
    能耗间接碳排放（Scope 2）总入口
    """

    def __init__(self, params: ModelParams):
        self.p = params
        self.M3 = AerationEnergyModel(params)
        self.M4 = OtherEnergyModel(params)

    def calculate_CO2eq(self, inp: ModelInput) -> float:
        """
        返回能耗间接碳排放 (kgCO₂eq/年)

        E_scope2 = E_total_annual × EF_grid
        """
        E_annual = inp.E_total_monthly * 12.0
        return E_annual * self.p.EF_grid
