#!/usr/bin/env python3
"""
AAO Process Python Simulator — OAKI Project
[SYNTHETIC-SIM] NOT actual BSM2G MATLAB output.
This is a Python-based simplified AAO differential equation simulator
approximating BSM2G-style dynamics for method development purposes.

Data label: [仿真-Python-AAO]
All outputs from this simulator must be labeled as synthetic simulation data.
They are NOT equivalent to actual BSM2G output or real plant measurements.

Reference structure based on:
- Henze et al. (2000) Activated Sludge Models ASM1, ASM2, ASM2d and ASM3
- Alex et al. (2008) BSM1 description, IWA
- Nopens et al. (2010) BSM2: a model for full-scale WWTP control
- Corominas et al. (2010) BSM2G GHG extension
"""
import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from dataclasses import dataclass, field
from typing import Dict, Tuple
import os, warnings
warnings.filterwarnings('ignore')

# ============================================================
# Default ASM1-like Parameters (literature prior)
# Source: Henze et al. 2000; Copp et al. 2002
# ============================================================
@dataclass
class AAOParams:
    """Four-layer parameter structure (research_design_v2.md Section 2.2.3)"""
    # --- Layer 1: Hard-frozen mechanistic structure ---
    stoich_Y_H: float = 0.67      # Heterotrophic yield (g COD/g COD) [Henze2000]
    stoich_Y_A: float = 0.24      # Autotrophic yield (g COD/g N) [Henze2000]
    stoich_f_p: float = 0.08      # Fraction of biomass as endogenous residue
    stoich_i_XB: float = 0.086    # N fraction in active biomass (g N/g COD)
    stoich_i_XP: float = 0.06     # N fraction in inert biomass

    # --- Layer 2: Shared prior parameters ---
    mu_H: float = 6.0             # Max heterotrophic growth rate (d⁻¹) @20°C [Henze2000: 4-8]
    K_S: float = 20.0             # Half-sat for soluble substrate (mg COD/L)
    K_OH: float = 0.2             # Half-sat DO for aerobes (mg O₂/L)
    K_NO: float = 0.5             # Half-sat NO₃ for anoxic growth
    b_H: float = 0.62             # Heterotrophic decay rate (d⁻¹) [Henze2000: 0.4-0.8]
    mu_A: float = 0.8             # Max autotrophic growth rate (d⁻¹) @20°C [Henze2000: 0.4-1.2]
    K_NH: float = 1.0             # Half-sat NH₄ for nitrification (mg N/L)
    K_OA: float = 0.4             # Half-sat DO for nitrification (mg O₂/L)
    b_A: float = 0.05             # Autotrophic decay rate (d⁻¹)
    eta_g: float = 0.8            # Anoxic correction factor
    eta_h: float = 0.4            # Anoxic hydrolysis correction
    k_h: float = 3.0              # Hydrolysis rate (d⁻¹)
    K_X: float = 0.03             # Half-sat for hydrolysis

    # --- Layer 3: Plant-level parameters (virtual plant specific) ---
    # AAO zones: [Anaerobic, Anoxic, Aerobic1, Aerobic2, Aerobic3]
    V_zones: np.ndarray = field(default_factory=lambda: np.array([600., 1200., 1400., 1400., 1400.]))  # m³
    DO_setpoints: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.2, 2.0, 2.0, 2.0]))     # mg/L
    KLa_max: float = 240.0        # Max KLa in aerobic zones (d⁻¹)
    Q_recycle_ratio: float = 2.0  # Internal recycle (Q_IR / Q_in)
    Q_RAS_ratio: float = 1.0      # Return sludge ratio
    MLSS_target: float = 3500.0   # mg TSS/L target
    SRT_target: float = 15.0      # days
    
    # Temperature correction (Arrhenius)
    theta_mu: float = 1.072       # Growth rate temp coeff [Metcalf&Eddy]
    theta_KLa: float = 1.024      # KLa temp coeff
    T_ref: float = 20.0           # Reference temp (°C)

    # --- Layer 4: Dynamic state (updated online) ---
    # These are initialized, not fixed
    
    # GHG parameters [SYNTHETIC APPROXIMATION]
    # N₂O: simplified AOB pathway + denitrification pathway
    # Based on ranges from: Kampschreur et al. 2009, Ni et al. 2011
    N2O_EF_nit: float = 0.005     # N₂O EF nitrification (gN₂O-N/gN_removed) [lit range 0.001-0.05]
    N2O_EF_denit: float = 0.002   # N₂O EF denitrification [lit range 0.001-0.015]
    N2O_DO_half: float = 1.5      # DO at which N₂O switches pathway (mg/L)
    
    # CH₄: simplified dissolved CH₄ stripping
    # Based on: Daelman et al. 2012, Guisasola et al. 2008
    CH4_inf_dissolved: float = 0.03   # Dissolved CH₄ in influent (mg CH₄/L) [lit: 0.01-0.1]
    CH4_K_La: float = 5.0             # CH₄ stripping coefficient in aerobic zones (d⁻¹)
    CH4_sat: float = 0.001            # CH₄ saturation (mg/L at 20°C, 1 atm)

    def temp_factor(self, T: float) -> Dict[str, float]:
        """Arrhenius temperature correction factors"""
        dT = T - self.T_ref
        return {
            'mu': self.theta_mu ** dT,
            'KLa': self.theta_KLa ** dT,
            'KLa_factor': self.theta_KLa ** dT
        }


# ============================================================
# Influent Generator
# ============================================================
class InfluentGenerator:
    """
    Generate synthetic influent time series
    Approximates BSM2G-style diurnal + seasonal variation
    """
    def __init__(self, Q_avg=40000., COD_avg=350., TN_avg=45., 
                 NH4_avg=35., TP_avg=5.5, seed=42):
        self.rng = np.random.default_rng(seed)
        self.Q_avg = Q_avg    # m³/d
        self.COD_avg = COD_avg
        self.TN_avg = TN_avg
        self.NH4_avg = NH4_avg
        self.TP_avg = TP_avg

    def generate(self, n_days=609, dt_min=15):
        """Generate 15-minute influent time series"""
        n_steps = int(n_days * 24 * 60 / dt_min)
        t_days = np.linspace(0, n_days, n_steps)
        t_hours = t_days * 24

        # Diurnal pattern (h): peak ~10:00 and ~20:00
        hour_of_day = t_hours % 24
        diurnal = 1.0 + 0.4 * np.sin(2*np.pi*(hour_of_day - 8)/24) + \
                        0.15 * np.sin(4*np.pi*(hour_of_day - 12)/24)

        # Seasonal pattern (summer low-concentration)
        day_of_year = (t_days % 365)
        seasonal = 1.0 - 0.15 * np.sin(2*np.pi*(day_of_year - 90)/365)

        # Dry/wet weather events (20% of days are wet weather)
        rain_prob = 0.15
        rain_events = np.zeros(n_steps)
        i = 0
        while i < n_steps:
            if self.rng.random() < rain_prob:
                dur = int(self.rng.uniform(4, 12) * 60 / dt_min)  # 4-12 hour events
                intensity = self.rng.uniform(1.2, 2.5)
                rain_events[i:min(i+dur, n_steps)] = intensity
                i += dur + int(24*60/dt_min)
            else:
                i += 1

        rain_factor = np.maximum(1.0, rain_events)
        noise = self.rng.normal(1.0, 0.05, n_steps)

        Q = self.Q_avg * diurnal * seasonal * rain_factor * noise
        Q = np.clip(Q, 0.1 * self.Q_avg, 3.0 * self.Q_avg)

        # Concentrations (inverse dilution with rain)
        dilution = np.where(rain_events > 1, 1.0/rain_factor, 1.0)
        conc_noise = self.rng.normal(1.0, 0.08, (5, n_steps))
        
        COD = np.clip(self.COD_avg * dilution * seasonal * conc_noise[0], 50, 800)
        TN  = np.clip(self.TN_avg  * dilution * seasonal * conc_noise[1], 15, 80)
        NH4 = np.clip(self.NH4_avg * dilution * seasonal * conc_noise[2] * 0.75, 5, 60)
        TP  = np.clip(self.TP_avg  * dilution * seasonal * conc_noise[3], 0.5, 15)
        SS  = np.clip(0.7 * COD * conc_noise[4], 20, 500)
        T   = 20 + 8 * np.sin(2*np.pi*(day_of_year - 90)/365) + \
              self.rng.normal(0, 0.5, n_steps)  # seasonal temp (12-28°C)
        T   = np.clip(T, 5, 35)
        
        # BOD ≈ 0.6*COD
        BOD = 0.6 * COD * self.rng.normal(1.0, 0.05, n_steps)
        
        # Dissolved CH₄ in influent (from septic conditions)
        CH4_diss = np.clip(
            0.03 * (1 + 0.5*np.sin(2*np.pi*day_of_year/365)) * self.rng.lognormal(0, 0.3, n_steps),
            0.001, 0.2
        )

        df = pd.DataFrame({
            't_days': t_days,
            'Q_m3d': Q,
            'COD_in': COD, 'BOD_in': BOD, 'TN_in': TN,
            'NH4_in': NH4, 'TP_in': TP, 'SS_in': SS,
            'T_water': T,
            'CH4_diss_in': CH4_diss,
            'is_rain': (rain_events > 1).astype(int)
        })
        return df


# ============================================================
# Simplified AAO Steady-State Approximator
# (Replaces full ODE integration for efficiency)
# ============================================================
class AAOSteadyStateModel:
    """
    Simplified AAO model using algebraic approximations.
    Captures key process dynamics without full Simulink-level ODE solving.
    Sufficient for multi-task learning data generation.
    """
    def __init__(self, params: AAOParams = None):
        self.p = params or AAOParams()

    def _temp_correct(self, rate, T, coeff):
        return rate * coeff**(T - self.p.T_ref)

    def compute_effluent(self, Q, COD_in, TN_in, NH4_in, TP_in, SS_in, T,
                         DO_aer=2.0, IR=2.0, RAS=1.0, SRT=15.0):
        """
        Compute effluent quality using semi-analytical approximation.
        Returns: dict of effluent concentrations + energy + GHG estimates
        """
        p = self.p
        tf = p.temp_factor(T)

        # --- 1. Anaerobic zone: EBPR (enhanced biological P removal) ---
        # Simple empirical: PAO release fraction depends on easily degradable COD
        VFA_fraction = 0.25  # fraction of COD as VFA available for PAO
        P_release = min(0.4 * COD_in * VFA_fraction / (50 + COD_in), TP_in * 0.6)

        # --- 2. Anoxic zone: Denitrification ---
        # Simplified: denitrification using internal recycle
        NO3_available = TN_in * 0.8  # ~80% as NO3 after nitrification
        # Readily biodegradable COD available for denitrification
        COD_anoxic = COD_in * 0.35 * p.eta_g  # fraction available in anoxic
        N_denit_capacity = COD_anoxic / (2.86 / (1 - p.stoich_Y_H))  # stoichiometric
        NO3_denit = min(N_denit_capacity, NO3_available * IR/(IR+1))
        
        # --- 3. Aerobic zone: Nitrification ---
        # Monod nitrification with temperature correction
        mu_A_T = self._temp_correct(p.mu_A, T, p.theta_mu)
        # NH4 removal efficiency based on SRT vs theta_c_min
        theta_c_min = 1.0 / (mu_A_T - p.b_A)
        SRT_factor = np.clip(SRT / (theta_c_min * 2), 0, 1)
        nitrif_efficiency = np.clip(SRT_factor * 0.97 * (DO_aer/(DO_aer + p.K_OA)), 0.6, 0.98)
        
        NH4_nit = NH4_in * nitrif_efficiency  # NH₄ nitrified
        NH4_out = max(NH4_in - NH4_nit, NH4_in * 0.02)
        NH4_out = max(NH4_out + np.random.normal(0, 0.3), 0.1)

        # --- 4. Overall N removal ---
        TN_removal = NO3_denit + NH4_nit * p.stoich_Y_A * 0  # simplified
        NO3_eff = max(NH4_nit - NO3_denit, 0)
        TN_out = max(TN_in - NH4_nit * 0.9 + NO3_eff * 0.5, TN_in * 0.1)
        TN_out = max(TN_out * (1 + np.random.normal(0, 0.08)), 1.0)

        # --- 5. COD removal ---
        mu_H_T = self._temp_correct(p.mu_H, T, p.theta_mu)
        COD_removal_eff = np.clip(0.92 + 0.05*(DO_aer-1)/(DO_aer+1), 0.80, 0.96)
        COD_out = max(COD_in * (1 - COD_removal_eff) + np.random.normal(0, 2), 5)

        # --- 6. TP removal ---
        P_uptake = P_release * 2.0 * RAS / (RAS + 1)  # PAO uptake in aerobes
        TP_out = max(TP_in - P_release + P_release - P_uptake, TP_in * 0.05)
        TP_out = max(TP_out + np.random.normal(0, 0.1), 0.05)
        TP_out = np.clip(TP_out, 0.05, TP_in)

        # --- 7. SS / MLSS ---
        SS_out = np.clip(COD_out * 0.6 + np.random.normal(0, 1), 2, 20)
        V_total = np.sum(p.V_zones)
        X_VSS = Q * p.stoich_Y_H * (COD_in - COD_out) * SRT / (V_total * (1 + p.b_H * SRT))
        MLSS = X_VSS / 0.75  # VSS/TSS ratio ~0.75

        # --- 8. Energy consumption ---
        # Aeration energy (dominant, 50-65% of total)
        Q_m3h = Q / 24
        # O₂ demand: BOD + nitrification - denitrification
        O2_demand_kgd = (
            Q/1e6 * ((COD_in - COD_out) * (1 - 1.42*p.stoich_Y_H) +  # COD removal
                     4.57 * NH4_nit -                                   # nitrification
                     2.86 * NO3_denit)                                  # denitrification credit
        ) * 1e3  # kg O₂/d
        # Standard oxygen transfer efficiency ~18%
        SOTE = 0.18
        air_density = 1.2  # kg/m³
        O2_in_air = 0.23
        air_flow = O2_demand_kgd / (SOTE * air_density * O2_in_air)  # m³/d air
        aeration_power = air_flow * 0.7 / (24 * 3600 * 0.7)  # kW (blower efficiency ~70%)
        E_aeration = aeration_power * 24 / (Q/1e4)  # kWh/万m³
        
        # Pumping + other
        E_pumping = 50 * (IR + RAS)  # kWh/万m³
        E_total_kWh_m3 = (E_aeration + E_pumping) * 1e-4 + 0.05  # convert to kWh/m³
        E_total_kWh_m3 = np.clip(E_total_kWh_m3, 0.15, 0.65)

        # --- 9. GHG Emissions [SYNTHETIC APPROXIMATION] ---
        # N₂O: pathway switching based on DO (Ni et al. 2011)
        # Pathway A (AOB oxidation): dominant at low DO
        # Pathway B (denitrification of NO₂⁻): dominant at high DO
        DO_switch = p.N2O_DO_half
        fA = np.exp(-DO_aer / DO_switch)  # Pathway A fraction
        fB = 1 - fA                        # Pathway B fraction
        N2O_nit = NH4_nit * (fA * p.N2O_EF_nit * 2.0 + fB * p.N2O_EF_nit * 0.5)
        N2O_denit = NO3_denit * p.N2O_EF_denit
        N2O_total_gN_m3 = (N2O_nit + N2O_denit) * Q / (Q + 1e-6)  # gN/m³ treated water
        N2O_EF_total = (N2O_nit + N2O_denit) / max(TN_in - TN_out, 0.1)

        # CH₄: stripping from dissolved + aerobic oxidation
        # Based on Daelman et al. 2012 framework
        CH4_in_dissolved = 0.03  # mg/L approximation
        CH4_stripped_aerobic = CH4_in_dissolved * (1 - np.exp(-p.CH4_K_La * V_total/np.sum(p.V_zones[2:])))
        CH4_total_gCH4_m3 = CH4_stripped_aerobic + 0.001  # baseline production
        
        # Convert to CO₂eq
        N2O_CO2eq = N2O_total_gN_m3 * 44/28 * 265 / 1000   # kg CO₂eq/m³ (GWP₁₀₀=265)
        CH4_CO2eq = CH4_total_gCH4_m3 * 28 / 1000           # kg CO₂eq/m³ (GWP₁₀₀=28)
        GHG_direct = N2O_CO2eq + CH4_CO2eq
        GHG_indirect = E_total_kWh_m3 * 0.581               # kg CO₂eq/m³ (CN grid 2024)
        GHG_total = GHG_direct + GHG_indirect

        return {
            # Effluent quality
            'NH4_out': float(NH4_out), 'TN_out': float(TN_out),
            'TP_out': float(TP_out), 'COD_out': float(COD_out), 'SS_out': float(SS_out),
            # Process state
            'NO3_eff': float(NO3_eff), 'MLSS': float(MLSS), 'SRT_est': float(SRT),
            'nitrif_eff': float(nitrif_efficiency),
            # Energy
            'E_kWh_m3': float(E_total_kWh_m3),
            'E_aeration_kWh_m3': float(E_aeration * 1e-4),
            # GHG [SYNTHETIC - NOT real measurements]
            'N2O_gN_m3': float(N2O_total_gN_m3),
            'N2O_EF': float(N2O_EF_total),
            'CH4_gCH4_m3': float(CH4_total_gCH4_m3),
            'GHG_direct_kgCO2eq_m3': float(GHG_direct),
            'GHG_indirect_kgCO2eq_m3': float(GHG_indirect),
            'GHG_total_kgCO2eq_m3': float(GHG_total),
        }


# ============================================================
# Virtual Plant Simulator
# ============================================================
class VirtualPlantSimulator:
    """
    Simulate 609-day AAO plant operation.
    Data labeled: [仿真-Python-AAO]
    """
    def __init__(self, params: AAOParams = None, seed: int = 42):
        self.model = AAOSteadyStateModel(params)
        self.seed = seed
        np.random.seed(seed)

    def simulate(self, Q_avg=40000., COD_avg=350., TN_avg=45., NH4_avg=35.,
                 TP_avg=5.5, T_avg=20., DO_setpoint=2.0, 
                 IR_ratio=2.0, RAS_ratio=1.0, SRT=15.0,
                 n_days=609, dt_min=15) -> pd.DataFrame:
        """
        Generate 609-day simulation at 15-minute intervals.
        Returns DataFrame with 16 inputs + 6 targets + GHG components.
        """
        gen = InfluentGenerator(Q_avg, COD_avg, TN_avg, NH4_avg, TP_avg, seed=self.seed)
        inf = gen.generate(n_days, dt_min)
        
        n = len(inf)
        results = []
        
        # Simulate with DO variation
        DO_base = DO_setpoint
        rng = np.random.default_rng(self.seed + 1)
        
        for i in range(n):
            row = inf.iloc[i]
            # DO fluctuation (±0.5 mg/L around setpoint)
            DO = np.clip(DO_base + rng.normal(0, 0.3), 0.2, 5.0)
            
            # Occasional DO disturbances
            if rng.random() < 0.02:
                DO = rng.uniform(0.2, 0.8)  # low DO event
            
            out = self.model.compute_effluent(
                Q=float(row.Q_m3d), COD_in=float(row.COD_in),
                TN_in=float(row.TN_in), NH4_in=float(row.NH4_in),
                TP_in=float(row.TP_in), SS_in=float(row.SS_in),
                T=float(row.T_water), DO_aer=DO,
                IR=IR_ratio, RAS=RAS_ratio, SRT=SRT
            )
            
            rec = {**row.to_dict(), 'DO_aerobic': DO, **out}
            results.append(rec)
            
            if (i+1) % 5000 == 0:
                print(f"  Simulated {i+1}/{n} steps ({(i+1)/n*100:.0f}%)")

        df = pd.DataFrame(results)
        df.attrs['data_source'] = '[仿真-Python-AAO]'
        df.attrs['note'] = 'NOT actual BSM2G output. Python AAO approximation for method dev.'
        df.attrs['seed'] = self.seed
        return df


# ============================================================
# Virtual Plant Factory (multiple plants for transfer learning)
# ============================================================
VIRTUAL_PLANT_CONFIGS = {
    'VPlant_A': {
        'Q_avg': 40000., 'COD_avg': 350., 'TN_avg': 45., 'NH4_avg': 35.,
        'TP_avg': 5.5, 'DO_setpoint': 2.0, 'IR_ratio': 2.0, 'SRT': 15.,
        'description': 'Baseline medium-scale plant, typical SZ conditions'
    },
    'VPlant_B': {
        'Q_avg': 80000., 'COD_avg': 280., 'TN_avg': 38., 'NH4_avg': 28.,
        'TP_avg': 4.0, 'DO_setpoint': 1.8, 'IR_ratio': 3.0, 'SRT': 18.,
        'description': 'Large-scale plant, lower C/N, higher recycle'
    },
    'VPlant_C': {
        'Q_avg': 15000., 'COD_avg': 420., 'TN_avg': 55., 'NH4_avg': 42.,
        'TP_avg': 7.0, 'DO_setpoint': 2.5, 'IR_ratio': 1.5, 'SRT': 12.,
        'description': 'Small-scale plant, high-load, shorter SRT'
    },
    'VPlant_D': {
        'Q_avg': 60000., 'COD_avg': 250., 'TN_avg': 35., 'NH4_avg': 25.,
        'TP_avg': 3.5, 'DO_setpoint': 1.5, 'IR_ratio': 4.0, 'SRT': 20.,
        'description': 'Low DO operation, high recycle, long SRT'
    },
}

def get_params_for_plant(plant_id: str) -> AAOParams:
    """Return modified params for each virtual plant"""
    p = AAOParams()
    if plant_id == 'VPlant_B':
        p.mu_A = 0.9; p.SRT_target = 18.
    elif plant_id == 'VPlant_C':
        p.mu_H = 7.0; p.K_S = 15.; p.SRT_target = 12.
    elif plant_id == 'VPlant_D':
        p.mu_A = 0.75; p.N2O_EF_nit = 0.008; p.SRT_target = 20.
    return p


if __name__ == '__main__':
    print("Testing AAO Python Simulator...")
    sim = VirtualPlantSimulator(seed=42)
    df = sim.simulate(n_days=5, dt_min=15)
    print(f"Generated: {len(df)} steps")
    print(df[['t_days','Q_m3d','COD_in','TN_in','NH4_in','NH4_out','TN_out',
              'E_kWh_m3','N2O_gN_m3','GHG_total_kgCO2eq_m3']].describe().to_string())
    print("\n[SYNTHETIC-SIM] All GHG values are Python approximation, NOT BSM2G output.")
