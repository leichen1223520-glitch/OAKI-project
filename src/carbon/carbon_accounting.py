"""
T076-T080: Full-Plant Carbon Accounting Module
Implements OAKI-Cal/Carbon accounting equations
Data sources: [真实活动数据] for indirect emissions, [仿真-Python-AAO] for direct GHG
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import warnings

# ─── Emission Factors (literature values) ────────────────────────────────────
@dataclass
class EmissionFactors:
    """
    Emission factors from literature/national standards
    [文献先验] - based on IPCC AR6, China GHG accounting standards
    """
    # GHG GWP100 (IPCC AR6, 2021)
    GWP_N2O: float = 273.0    # CO2eq per unit N2O [IPCC AR6]
    GWP_CH4: float = 27.9     # CO2eq per unit CH4 [IPCC AR6]
    
    # Grid electricity emission factor (China, 2022)
    # Source: MEE China 2022 National Grid Emission Factors
    # Regional variation: 0.40 (Yunnan) ~ 0.90 (Northeast)
    EF_electricity_kgCO2_kWh: float = 0.581  # National average [MEE 2022]
    EF_electricity_std: float = 0.08           # Uncertainty ±1σ
    
    # Chemical dosing emission factors [文献先验]
    # Source: Ecoinvent v3.9 / Fenu et al. 2010
    EF_ferric_sulfate_kgCO2_kg: float = 0.35   # FeSO4 for P removal
    EF_sodium_acetate_kgCO2_kg: float = 1.42   # External carbon source
    EF_polymer_kgCO2_kg: float = 2.20           # Polyacrylamide for dewatering
    EF_lime_kgCO2_kg: float = 0.78              # CaO for pH adjustment
    
    # Sludge disposal emission factors
    # Source: Yoshida et al. 2013; Wang et al. 2019 (China context)
    EF_sludge_landfill_kgCO2_tDS: float = 0.45     # Landfill (CH4 from degradation)
    EF_sludge_incineration_kgCO2_tDS: float = 1.20  # Incineration
    EF_sludge_composting_kgCO2_tDS: float = 0.28    # Composting
    EF_sludge_land_apply_kgCO2_tDS: float = 0.15    # Land application
    
    # Credits
    EF_biogas_credit_kgCO2_m3: float = -1.52    # Biogas electricity credit
    EF_reclaimed_water_kgCO2_m3: float = -0.10  # Reclaimed water credit


@dataclass 
class CarbonAccountingConfig:
    """Plant-level carbon accounting configuration"""
    # System boundary: Scope 1/2 (process + energy), Scope 3 partial
    include_scope1_n2o: bool = True
    include_scope1_ch4: bool = True
    include_scope2_electricity: bool = True
    include_scope3_chemicals: bool = True
    include_scope3_sludge: bool = True
    include_credits: bool = False
    
    # Data quality flags
    n2o_from_measurement: bool = False   # True only if real flux data
    ch4_from_measurement: bool = False   # True only if real flux data
    
    # Default sludge disposal route
    sludge_route: str = 'landfill'   # landfill/incineration/composting/land_apply


class PlantCarbonAccounting:
    """
    Full-plant carbon accounting model.
    
    IMPORTANT: Direct GHG (N2O, CH4) from [仿真-Python-AAO] unless real data provided.
    Indirect emissions from [真实活动数据] (46-plant monthly).
    """
    
    def __init__(self, ef: EmissionFactors = None, cfg: CarbonAccountingConfig = None):
        self.ef = ef or EmissionFactors()
        self.cfg = cfg or CarbonAccountingConfig()
    
    def compute_direct_ghg(self, Q_m3: float, N2O_gN_m3: float, CH4_gCH4_m3: float,
                            data_source: str = '[仿真-Python-AAO]') -> Dict:
        """
        Compute direct GHG emissions (Scope 1)
        Q_m3: treated volume (m³)
        N2O_gN_m3: N2O emission rate (g N-N2O / m³ treated)
        CH4_gCH4_m3: CH4 emission rate (g CH4 / m³ treated)
        """
        # N2O: g N/m³ → kg N2O/m³ → kg CO2eq/m³
        N2O_kgN2O_m3 = N2O_gN_m3 * 44./28. / 1000.    # gN → kg N2O
        E_N2O_kgCO2eq_m3 = N2O_kgN2O_m3 * self.ef.GWP_N2O
        E_N2O_total = E_N2O_kgCO2eq_m3 * Q_m3           # kg CO2eq
        
        # CH4: g CH4/m³ → kg CO2eq/m³
        CH4_kgCH4_m3 = CH4_gCH4_m3 / 1000.
        E_CH4_kgCO2eq_m3 = CH4_kgCH4_m3 * self.ef.GWP_CH4
        E_CH4_total = E_CH4_kgCO2eq_m3 * Q_m3
        
        E_direct = E_N2O_total + E_CH4_total
        
        return {
            'E_N2O_kgCO2eq': E_N2O_total,
            'E_N2O_kgCO2eq_m3': E_N2O_kgCO2eq_m3,
            'E_CH4_kgCO2eq': E_CH4_total,
            'E_CH4_kgCO2eq_m3': E_CH4_kgCO2eq_m3,
            'E_direct_kgCO2eq': E_direct,
            'E_direct_kgCO2eq_m3': E_direct / max(Q_m3, 1.),
            'data_source_ghg': data_source
        }
    
    def compute_indirect_electricity(self, Q_m3: float, E_kWh_m3: float,
                                      EF_override: Optional[float] = None) -> Dict:
        """Compute indirect emissions from electricity (Scope 2)"""
        ef = EF_override or self.ef.EF_electricity_kgCO2_kWh
        E_elec_kWh = E_kWh_m3 * Q_m3
        E_elec_kgCO2eq = E_elec_kWh * ef
        
        return {
            'E_electricity_kWh': E_elec_kWh,
            'E_electricity_kgCO2eq': E_elec_kgCO2eq,
            'E_electricity_kgCO2eq_m3': E_elec_kgCO2eq / max(Q_m3, 1.),
            'EF_electricity_used': ef,
            'data_source_elec': '[真实活动数据]' if E_kWh_m3 > 0 else '[估算]'
        }
    
    def compute_chemicals(self, Q_m3: float,
                           ferric_kg_m3: float = 0.0,
                           carbon_source_kg_m3: float = 0.0,
                           polymer_kg_m3: float = 0.0) -> Dict:
        """Compute indirect emissions from chemical dosing (Scope 3 partial)"""
        E_ferric  = ferric_kg_m3 * Q_m3 * self.ef.EF_ferric_sulfate_kgCO2_kg
        E_carbon  = carbon_source_kg_m3 * Q_m3 * self.ef.EF_sodium_acetate_kgCO2_kg
        E_polymer = polymer_kg_m3 * Q_m3 * self.ef.EF_polymer_kgCO2_kg
        E_chem = E_ferric + E_carbon + E_polymer
        
        return {
            'E_ferric_kgCO2eq': E_ferric,
            'E_carbon_source_kgCO2eq': E_carbon,
            'E_polymer_kgCO2eq': E_polymer,
            'E_chemicals_kgCO2eq': E_chem,
            'E_chemicals_kgCO2eq_m3': E_chem / max(Q_m3, 1.)
        }
    
    def compute_sludge(self, Q_m3: float, sludge_tDS_m3: float = 0.0,
                        route: Optional[str] = None) -> Dict:
        """Compute indirect emissions from sludge disposal (Scope 3)"""
        route = route or self.cfg.sludge_route
        EF_map = {
            'landfill': self.ef.EF_sludge_landfill_kgCO2_tDS,
            'incineration': self.ef.EF_sludge_incineration_kgCO2_tDS,
            'composting': self.ef.EF_sludge_composting_kgCO2_tDS,
            'land_apply': self.ef.EF_sludge_land_apply_kgCO2_tDS,
        }
        ef_sludge = EF_map.get(route, self.ef.EF_sludge_landfill_kgCO2_tDS)
        sludge_tDS = sludge_tDS_m3 * Q_m3 / 1000.  # tDS
        E_sludge = sludge_tDS * ef_sludge * 1000.   # kg CO2eq
        
        return {
            'sludge_tDS': sludge_tDS,
            'E_sludge_kgCO2eq': E_sludge,
            'E_sludge_kgCO2eq_m3': E_sludge / max(Q_m3, 1.),
            'sludge_route': route
        }
    
    def compute_total(self, Q_m3: float,
                       N2O_gN_m3: float = 0.11,       # [仿真-Python-AAO] default
                       CH4_gCH4_m3: float = 0.001,     # [仿真-Python-AAO] default
                       E_kWh_m3: float = 0.35,          # typical SZ plant
                       sludge_tDS_m3: float = 0.0002,
                       ferric_kg_m3: float = 0.02,
                       carbon_source_kg_m3: float = 0.0,
                       polymer_kg_m3: float = 0.001,
                       ghg_data_source: str = '[仿真-Python-AAO]') -> Dict:
        """Compute total carbon footprint"""
        
        d = self.compute_direct_ghg(Q_m3, N2O_gN_m3, CH4_gCH4_m3, ghg_data_source)
        e = self.compute_indirect_electricity(Q_m3, E_kWh_m3)
        c = self.compute_chemicals(Q_m3, ferric_kg_m3, carbon_source_kg_m3, polymer_kg_m3)
        s = self.compute_sludge(Q_m3, sludge_tDS_m3)
        
        E_total = (d['E_direct_kgCO2eq'] + e['E_electricity_kgCO2eq'] +
                   c['E_chemicals_kgCO2eq'] + s['E_sludge_kgCO2eq'])
        
        return {
            **d, **e, **c, **s,
            'E_total_kgCO2eq': E_total,
            'E_total_kgCO2eq_m3': E_total / max(Q_m3, 1.),
            'Q_m3': Q_m3,
            # Breakdown fractions
            'frac_N2O': d['E_N2O_kgCO2eq'] / max(E_total, 1e-9),
            'frac_CH4': d['E_CH4_kgCO2eq'] / max(E_total, 1e-9),
            'frac_electricity': e['E_electricity_kgCO2eq'] / max(E_total, 1e-9),
            'frac_chemicals': c['E_chemicals_kgCO2eq'] / max(E_total, 1e-9),
            'frac_sludge': s['E_sludge_kgCO2eq'] / max(E_total, 1e-9),
        }
    
    def monte_carlo_uncertainty(self, base_params: Dict, n_samples: int = 1000,
                                 seed: int = 42) -> Dict:
        """
        Monte Carlo uncertainty propagation (T079)
        Returns 95% CI for total carbon footprint
        """
        rng = np.random.default_rng(seed)
        totals = []
        
        for _ in range(n_samples):
            # Sample uncertain parameters
            N2O_sample = rng.lognormal(
                np.log(max(base_params.get('N2O_gN_m3', 0.11), 1e-6)), 0.4)
            CH4_sample = rng.lognormal(
                np.log(max(base_params.get('CH4_gCH4_m3', 0.001), 1e-6)), 0.5)
            E_sample = base_params.get('E_kWh_m3', 0.35) * rng.normal(1., 0.08)
            EF_elec_sample = self.ef.EF_electricity_kgCO2_kWh * rng.normal(1., 0.15)
            
            result = self.compute_total(
                Q_m3=base_params['Q_m3'],
                N2O_gN_m3=max(N2O_sample, 1e-6),
                CH4_gCH4_m3=max(CH4_sample, 1e-8),
                E_kWh_m3=max(E_sample, 0.1),
                **{k: v for k, v in base_params.items() 
                   if k not in ['Q_m3','N2O_gN_m3','CH4_gCH4_m3','E_kWh_m3']}
            )
            # Override electricity EF
            result2 = self.compute_indirect_electricity(
                base_params['Q_m3'], max(E_sample, 0.1), EF_elec_sample)
            tot = (result['E_N2O_kgCO2eq'] + result['E_CH4_kgCO2eq'] +
                   result2['E_electricity_kgCO2eq'] + result['E_chemicals_kgCO2eq'] +
                   result['E_sludge_kgCO2eq'])
            totals.append(tot / max(base_params['Q_m3'], 1.))
        
        totals = np.array(totals)
        return {
            'mean': float(totals.mean()),
            'std': float(totals.std()),
            'p2.5': float(np.percentile(totals, 2.5)),
            'p97.5': float(np.percentile(totals, 97.5)),
            'p50': float(np.percentile(totals, 50)),
            'n_samples': n_samples
        }


def compute_46plant_carbon(panel_df: pd.DataFrame, 
                             ef: EmissionFactors = None) -> pd.DataFrame:
    """
    T080: Compute carbon inventory for 46-plant panel
    Data: [真实活动数据] for indirect; [仿真-Python-AAO] default for direct
    """
    ef = ef or EmissionFactors()
    model = PlantCarbonAccounting(ef)
    
    results = []
    for _, row in panel_df.iterrows():
        Q_m3 = float(row.get('Q_wan_m3', 0)) * 1e4  # 万m³ → m³/month
        
        # Energy from data or estimate (T030 approach)
        E_kWh_m3 = float(row.get('E_kWh_m3', np.nan))
        if np.isnan(E_kWh_m3) or E_kWh_m3 <= 0:
            # Estimate from load using regression approximation
            COD_in = float(row.get('COD_in_mgL', 300.))
            TN_in  = float(row.get('TN_in_mgL', 40.))
            # Simple empirical: E ~ 0.15 + 0.0008*COD_in + 0.003*TN_in
            E_kWh_m3 = max(0.15 + 0.0008*COD_in + 0.003*TN_in, 0.15)
            E_source = '[估算-回归]'
        else:
            E_source = '[真实活动数据]'
        
        # Direct GHG: use default simulation-based estimate
        # NOTE: No real GHG data → use [仿真-Python-AAO] typical value
        N2O_gN_m3_default = 0.11   # from VPlant_A simulation
        CH4_gCH4_m3_default = 0.001
        
        # Typical chemical dosing (SZ conditions, literature estimates)
        ferric_kg_m3 = 0.025   # g/L FeSO4 (literature range 0.01-0.05)
        
        # Sludge production estimate: ~0.2-0.4 kg DS / kg COD removed
        COD_in_mgL = float(row.get('COD_in_mgL', 300.))
        COD_out_mgL = float(row.get('COD_out_mgL', 10.))
        sludge_tDS_m3 = max(0.00025*(COD_in_mgL - COD_out_mgL)/1000., 0.0001)
        
        result = model.compute_total(
            Q_m3=Q_m3, N2O_gN_m3=N2O_gN_m3_default,
            CH4_gCH4_m3=CH4_gCH4_m3_default,
            E_kWh_m3=E_kWh_m3, sludge_tDS_m3=sludge_tDS_m3,
            ferric_kg_m3=ferric_kg_m3,
            ghg_data_source='[仿真-Python-AAO-default]'
        )
        
        out_row = {
            'plant_id': row.get('plant_id',''),
            'plant_alias': row.get('plant_alias',''),
            'month': row.get('month',''),
            'month_num': row.get('month_num', 0),
            'Q_m3': Q_m3,
            'E_kWh_m3': E_kWh_m3, 'E_source': E_source,
            **result,
            'note': 'Direct GHG: [仿真-Python-AAO-default]. Indirect: [真实活动数据]/[估算].'
        }
        results.append(out_row)
    
    return pd.DataFrame(results)


if __name__ == '__main__':
    # Quick test
    model = PlantCarbonAccounting()
    result = model.compute_total(Q_m3=1e6, N2O_gN_m3=0.11, E_kWh_m3=0.35)
    print("Test carbon accounting:")
    for k, v in result.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
    
    unc = model.monte_carlo_uncertainty({'Q_m3':1e6,'N2O_gN_m3':0.11,'E_kWh_m3':0.35}, n_samples=500)
    print(f"\nUncertainty (95% CI): [{unc['p2.5']:.4f}, {unc['p97.5']:.4f}] kgCO2eq/m³")
