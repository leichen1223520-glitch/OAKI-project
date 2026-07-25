#!/usr/bin/env python3
"""
Vectorized AAO Simulator — fast batch version
[仿真-Python-AAO] NOT actual BSM2G MATLAB output
"""
import numpy as np
import pandas as pd
import os, json

SEED = 42
OUT = 'data/processed/bsm2g'
os.makedirs(OUT, exist_ok=True)

def generate_influent(n_days=609, dt_min=15, Q_avg=40000, COD_avg=350,
                      TN_avg=45, NH4_avg=35, TP_avg=5.5, seed=42):
    """Vectorized influent generator — much faster"""
    rng = np.random.default_rng(seed)
    n = int(n_days * 24 * 60 / dt_min)
    t = np.linspace(0, n_days, n)
    
    hour = (t * 24) % 24
    doy  = t % 365
    
    diurnal  = 1. + 0.4*np.sin(2*np.pi*(hour-8)/24) + 0.15*np.sin(4*np.pi*(hour-12)/24)
    seasonal = 1. - 0.15*np.sin(2*np.pi*(doy-90)/365)
    
    # Rain events (vectorized)
    rain = np.zeros(n)
    i = 0
    while i < n:
        if rng.random() < 0.12:
            dur = int(rng.uniform(4,12)*60/dt_min)
            rain[i:min(i+dur,n)] = rng.uniform(1.2, 2.5)
            i += dur + int(24*60/dt_min)
        else:
            i += 1
    rain = np.maximum(rain, 1.)
    
    noise = rng.normal(1., 0.05, (6, n))
    dilut = np.where(rain > 1, 1./rain, 1.)
    
    Q   = np.clip(Q_avg   * diurnal * seasonal * rain * noise[0], 0.1*Q_avg, 3.*Q_avg)
    COD = np.clip(COD_avg * dilut * seasonal * noise[1], 50, 800)
    TN  = np.clip(TN_avg  * dilut * seasonal * noise[2], 15, 80)
    NH4 = np.clip(NH4_avg * dilut * seasonal * noise[3]*0.78, 5, 60)
    TP  = np.clip(TP_avg  * dilut * seasonal * noise[4], 0.5, 15)
    SS  = np.clip(0.7*COD * noise[5], 20, 500)
    BOD = 0.6*COD*rng.normal(1.,0.05,n)
    T_w = np.clip(20 + 8*np.sin(2*np.pi*(doy-90)/365) + rng.normal(0,.5,n), 5, 35)
    is_rain = (rain>1).astype(int)
    
    return pd.DataFrame({'t_days':t,'Q_m3d':Q,'COD_in':COD,'BOD_in':BOD,'TN_in':TN,
                          'NH4_in':NH4,'TP_in':TP,'SS_in':SS,'T_water':T_w,'is_rain':is_rain})

def compute_effluent_vec(inf_df, DO_setpoint=2.0, IR=2.0, RAS=1.0, SRT=15.0,
                          mu_A=0.8, mu_H=6.0, N2O_EF_nit=0.005, seed=42):
    """Vectorized effluent computation"""
    rng = np.random.default_rng(seed+1)
    n = len(inf_df)
    
    Q   = inf_df.Q_m3d.values
    COD = inf_df.COD_in.values
    TN  = inf_df.TN_in.values
    NH4 = inf_df.NH4_in.values
    TP  = inf_df.TP_in.values
    T   = inf_df.T_water.values
    
    # DO with noise
    DO = np.clip(DO_setpoint + rng.normal(0,.3,n), 0.2, 5.)
    # Low DO events
    lo = rng.random(n) < 0.02
    DO[lo] = rng.uniform(0.2, 0.8, lo.sum())
    
    # Temperature correction
    theta = 1.072
    tf_mu = theta**(T - 20.)
    
    # Nitrification
    b_A = 0.05; K_OA = 0.4
    theta_min = 1.0/(mu_A*tf_mu - b_A)
    theta_min = np.clip(theta_min, 0.5, 5.)
    SRT_fac = np.clip(SRT/(theta_min*2.), 0., 1.)
    nit_eff = np.clip(SRT_fac * 0.97 * DO/(DO+K_OA), 0.6, 0.98)
    
    NH4_nit = NH4 * nit_eff
    NH4_out = np.clip(NH4 - NH4_nit + rng.normal(0,.3,n), 0.1, NH4)
    
    # Denitrification
    Y_H = 0.67; eta_g = 0.8
    COD_anox = COD * 0.35 * eta_g
    N_denit = np.minimum(COD_anox / (2.86/(1-Y_H)), TN*0.8*IR/(IR+1))
    
    NO3_eff  = np.maximum(NH4_nit - N_denit, 0.)
    TN_out   = np.clip(TN - NH4_nit*0.85 + NO3_eff*0.5 + rng.normal(0,1.2,n), 1., TN)
    
    # COD removal
    COD_eff = np.clip(0.92 + 0.04*(DO-1.)/(DO+1.), 0.80, 0.96)
    COD_out = np.clip(COD*(1-COD_eff) + rng.normal(0,2,n), 5, 80)
    
    # P removal (simplified)
    P_release = np.minimum(0.4*COD*0.25/(50+COD), TP*0.6)
    P_uptake  = P_release * 1.8 * RAS/(RAS+1.)
    TP_out    = np.clip(TP - P_uptake + rng.normal(0,.1,n), 0.05, TP)
    SS_out    = np.clip(COD_out*0.6 + rng.normal(0,1,n), 2., 20.)
    
    # MLSS
    V_total = 6000.  # m³
    b_H = 0.62
    X_VSS = Q * Y_H * (COD-COD_out)*SRT / (V_total*(1+b_H*SRT)) / 1e3  # rough
    MLSS = np.clip(X_VSS/0.75, 1000, 8000)
    
    # Energy
    O2_demand = Q/1e6*((COD-COD_out)*(1-1.42*Y_H) + 4.57*NH4_nit - 2.86*N_denit)*1e3
    O2_demand = np.maximum(O2_demand, 0.)
    air_flow  = O2_demand/(0.18*1.2*0.23)
    aeration_kW = air_flow*0.7/(24*3600*0.7)
    E_aer = aeration_kW*24/(Q/1e4 + 1e-3)
    E_pump = 50*(IR+RAS)
    E = np.clip((E_aer+E_pump)*1e-4 + 0.05, 0.15, 0.65)
    
    # N₂O (pathway switching, DO-dependent)
    DO_sw = 1.5
    fA = np.exp(-DO/DO_sw)
    N2O_nit   = NH4_nit*(fA*N2O_EF_nit*2. + (1-fA)*N2O_EF_nit*0.5)
    N2O_denit = N_denit*0.002
    N2O       = (N2O_nit + N2O_denit) + rng.exponential(0.002,n)
    N2O_EF    = N2O / np.maximum(TN-TN_out, 0.1)
    
    # CH₄
    CH4_strip = 0.03*(1-np.exp(-5.*3400/V_total))
    CH4 = np.full(n, CH4_strip+0.001) + rng.exponential(0.0005,n)
    
    # GHG
    GHG_d = N2O*44/28*265/1e3 + CH4*28/1e3
    GHG_i = E*0.581
    GHG   = GHG_d + GHG_i
    
    return pd.DataFrame({
        'DO_aerobic':DO,'MLSS':MLSS,'nitrif_eff':nit_eff,'SRT_est':np.full(n,SRT),
        'NH4_out':NH4_out,'TN_out':TN_out,'TP_out':TP_out,'COD_out':COD_out,'SS_out':SS_out,
        'NO3_eff':NO3_eff,'E_kWh_m3':E,'E_aeration':E_aer*1e-4,
        'N2O_gN_m3':N2O,'N2O_EF':N2O_EF,'CH4_gCH4_m3':CH4,
        'GHG_direct_kgCO2eq_m3':GHG_d,'GHG_indirect_kgCO2eq_m3':GHG_i,
        'GHG_total_kgCO2eq_m3':GHG
    })

def simulate_plant(plant_id, Q_avg=40000, COD_avg=350, TN_avg=45, NH4_avg=35,
                   TP_avg=5.5, DO_sp=2.0, IR=2.0, SRT=15., n_days=609, dt=15, seed=42,
                   mu_A=0.8, N2O_EF=0.005):
    print(f'  Generating influent for {plant_id}...')
    inf = generate_influent(n_days, dt, Q_avg, COD_avg, TN_avg, NH4_avg, TP_avg, seed)
    print(f'  Computing effluent...')
    eff = compute_effluent_vec(inf, DO_sp, IR, 1.0, SRT, N2O_EF_nit=N2O_EF, seed=seed)
    df = pd.concat([inf, eff], axis=1)
    df['datetime']     = pd.date_range('2023-01-01', periods=len(df), freq=f'{dt}min')
    df['data_source']  = '[仿真-Python-AAO]'
    df['plant_id']     = plant_id
    df['phase']        = np.where(df.t_days < 245, 'warmup', 'evaluation')
    # Regime
    reg = np.full(len(df),'normal',dtype=object)
    reg[df.is_rain==1]          = 'wet'
    reg[df.Q_m3d > Q_avg*1.5]   = 'high_load'
    reg[df.T_water < 15]         = 'winter'
    reg[df.T_water > 25]         = 'summer'
    df['regime_label'] = reg
    return df

# ── T018: VPlant_A 609d standard ─────────────────────────────────────────────
print('='*60)
print('T018-T025: Generating simulation datasets')
print('[仿真-Python-AAO]')
print('='*60)

INPUT_COLS  = ['Q_m3d','COD_in','BOD_in','TN_in','NH4_in','TP_in','SS_in',
               'T_water','DO_aerobic','is_rain','MLSS','nitrif_eff','SRT_est',
               't_days','E_kWh_m3','COD_out']
TARGET_COLS = ['NH4_out','TN_out','TP_out','E_kWh_m3','N2O_gN_m3','GHG_total_kgCO2eq_m3']

configs = {
    'VPlant_A':{'Q':40000,'COD':350,'TN':45,'NH4':35,'TP':5.5,'DO':2.0,'IR':2.0,'SRT':15,'days':609,'mu_A':0.80,'N2O_EF':0.005},
    'VPlant_B':{'Q':80000,'COD':280,'TN':38,'NH4':28,'TP':4.0,'DO':1.8,'IR':3.0,'SRT':18,'days':365,'mu_A':0.90,'N2O_EF':0.004},
    'VPlant_C':{'Q':15000,'COD':420,'TN':55,'NH4':42,'TP':7.0,'DO':2.5,'IR':1.5,'SRT':12,'days':365,'mu_A':0.75,'N2O_EF':0.007},
    'VPlant_D':{'Q':60000,'COD':250,'TN':35,'NH4':25,'TP':3.5,'DO':1.5,'IR':4.0,'SRT':20,'days':365,'mu_A':0.72,'N2O_EF':0.009},
}

all_dfs = {}
for pid, cfg in configs.items():
    print(f'\n{pid}: {cfg["days"]}d @ 15min')
    df = simulate_plant(pid, cfg['Q'],cfg['COD'],cfg['TN'],cfg['NH4'],cfg['TP'],
                        cfg['DO'],cfg['IR'],cfg['SRT'],cfg['days'],15,
                        SEED + sum(ord(c) for c in pid) % 100,
                        cfg['mu_A'], cfg['N2O_EF'])
    df.to_csv(f'{OUT}/{pid}_{cfg["days"]}d_15min_v1.csv', index=False)
    all_dfs[pid] = df
    ev = df[df.phase=='evaluation']
    print(f'  {len(ev)} eval steps | NH4_out={ev.NH4_out.mean():.2f} | '
          f'TN_out={ev.TN_out.mean():.2f} | N2O={ev.N2O_gN_m3.mean()*1000:.2f}mgN/m³ | '
          f'E={ev.E_kWh_m3.mean():.3f}kWh/m³')

# ── T021: Sliding window dataset for VPlant_A ─────────────────────────────────
print('\n--- T021: Sliding window samples ---')
df_A = all_dfs['VPlant_A']
ev_A = df_A[df_A.phase=='evaluation'].reset_index(drop=True)
LB, HZ, STRIDE = 16, 4, 1
n_ev = len(ev_A)
n_samp = (n_ev - LB - HZ + 1)//STRIDE
print(f'Evaluation steps: {n_ev}, Samples: {n_samp}')

X_arr = np.lib.stride_tricks.sliding_window_view(
    ev_A[INPUT_COLS].values, (LB+HZ, len(INPUT_COLS))
)[::STRIDE, 0, :LB, :]  # (n, LB, feats)
y_arr = np.lib.stride_tricks.sliding_window_view(
    ev_A[TARGET_COLS].values, (LB+HZ, len(TARGET_COLS))
)[::STRIDE, 0, LB:, :]  # (n, HZ, targets)
print(f'X: {X_arr.shape}, y: {y_arr.shape}')

# Time split 80/20
n_tr = int(0.8 * len(X_arr))
tr_mask = np.zeros(len(X_arr), bool); tr_mask[:n_tr] = True
te_mask = ~tr_mask

# Scale (fit on train)
Xf  = X_arr[tr_mask].reshape(-1, len(INPUT_COLS))
Xmu = Xf.mean(0); Xsd = Xf.std(0)+1e-8
yf  = y_arr[tr_mask].reshape(-1, len(TARGET_COLS))
ymu = yf.mean(0); ysd = yf.std(0)+1e-8

X_sc = (X_arr - Xmu) / Xsd
y_sc = (y_arr - ymu) / ysd

np.save(f'{OUT}/X_VPlantA_v1.npy', X_arr)
np.save(f'{OUT}/y_VPlantA_v1.npy', y_arr)
np.save(f'{OUT}/X_scaled_VPlantA_v1.npy', X_sc)
np.save(f'{OUT}/y_scaled_VPlantA_v1.npy', y_sc)
np.save(f'{OUT}/train_mask_v1.npy', tr_mask)
np.save(f'{OUT}/test_mask_v1.npy',  te_mask)

scale = {'X_mean':Xmu.tolist(),'X_std':Xsd.tolist(),
         'y_mean':ymu.tolist(),'y_std':ysd.tolist(),
         'input_cols':INPUT_COLS,'target_cols':TARGET_COLS,'lookback':LB,'horizon':HZ}
with open(f'{OUT}/scaling_VPlantA_v1.json','w') as f:
    json.dump(scale, f, indent=2)
print(f'Train: {tr_mask.sum()}, Test: {te_mask.sum()}')

# ── Masking schemes ───────────────────────────────────────────────────────────
mask_dir = f'{OUT}/masks'; os.makedirs(mask_dir, exist_ok=True)
rng_m = np.random.default_rng(456)
ghg_idx = [4, 5]
n_tr_samp = tr_mask.sum()
for ratio in [0.0,0.2,0.4,0.6,0.8,0.9,0.95]:
    mask = np.ones((n_tr_samp, HZ, len(TARGET_COLS)), bool)
    for gi in ghg_idx:
        n_mk = int(n_tr_samp * ratio)
        mk = rng_m.choice(n_tr_samp, n_mk, replace=False)
        mask[mk,:,gi] = False
    np.save(f'{mask_dir}/mask_ghg_{int(ratio*100):03d}_seed456.npy', mask)
print('Masking schemes saved.')

# Few-shot calibration indices
cal_dir = f'{OUT}/few_shot'; os.makedirs(cal_dir, exist_ok=True)
te_idx = np.where(te_mask)[0]
for nd in [1,3,7,14,30]:
    nc = nd * 96  # 96 steps/day at 15min
    np.save(f'{cal_dir}/cal_{nd}d_indices.npy', te_idx[:nc])
print('Few-shot calibration indices saved.')

# ── T024: QA Summary ─────────────────────────────────────────────────────────
print('\n--- T024: Data Quality Summary ---')
qa = {}
for pid, df in all_dfs.items():
    ev = df[df.phase=='evaluation']
    row = {'n_steps':len(ev),'missing_pct':ev.isnull().mean().mean()*100}
    for col in TARGET_COLS:
        row[f'{col}_mean'] = float(ev[col].mean())
        row[f'{col}_std']  = float(ev[col].std())
    qa[pid] = row
    print(f'{pid}: {len(ev)} eval | '
          f'NH4_out={ev.NH4_out.mean():.2f}±{ev.NH4_out.std():.2f} | '
          f'N2O={ev.N2O_gN_m3.mean()*1000:.2f}mgN/m³ | '
          f'GHG={ev.GHG_total_kgCO2eq_m3.mean():.4f}kgCO₂eq/m³')
with open(f'{OUT}/qa_report.json','w') as f:
    json.dump(qa, f, indent=2)

print(f'\nAll datasets saved to {OUT}/')
print('[仿真-Python-AAO] NOT BSM2G MATLAB output. Labels required for all publications.')
