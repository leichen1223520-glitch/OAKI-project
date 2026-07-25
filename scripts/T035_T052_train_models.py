#!/usr/bin/env python3
"""
T035-T052: Train all baselines and OAKI-PL
[仿真-Python-AAO] data - results are synthetic simulation only
"""
import sys, os, json, time
sys.path.insert(0, '/workspace/OAKI-project')
import numpy as np
import torch, torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from src.models.baselines import (PersistenceBaseline, RidgeBaseline,
                                    LightGBMBaseline, GRUBaseline, AttMMoE)
from src.models.oaki_pl import (OAKI_PL, PartialLabelLoss,
                                  train_epoch, evaluate,
                                  TARGET_NAMES, GHG_TASK_IDX)

SEED = 42; torch.manual_seed(SEED); np.random.seed(SEED)
DATA_DIR = 'data/processed/bsm2g'
OUT_DIR  = 'results'
os.makedirs(f'{OUT_DIR}/models', exist_ok=True)
os.makedirs(f'{OUT_DIR}/tables', exist_ok=True)

print("Loading data [仿真-Python-AAO]...")
X_sc  = np.load(f'{DATA_DIR}/X_scaled_VPlantA_v1.npy').astype(np.float32)
y_sc  = np.load(f'{DATA_DIR}/y_scaled_VPlantA_v1.npy').astype(np.float32)
tr_mask = np.load(f'{DATA_DIR}/train_mask_v1.npy')
te_mask = np.load(f'{DATA_DIR}/test_mask_v1.npy')
with open(f'{DATA_DIR}/scaling_VPlantA_v1.json') as f:
    scale = json.load(f)
y_mean = np.array(scale['y_mean'], dtype=np.float32)
y_std  = np.array(scale['y_std'],  dtype=np.float32)

X_tr, X_te = X_sc[tr_mask], X_sc[te_mask]
y_tr, y_te = y_sc[tr_mask], y_sc[te_mask]
print(f"Train: {X_tr.shape}, Test: {X_te.shape}")

N_IN = X_tr.shape[2]; HORIZON = y_tr.shape[1]; N_TASKS = y_tr.shape[2]

tr_loader = DataLoader(TensorDataset(torch.from_numpy(X_tr), torch.from_numpy(y_tr)),
                        batch_size=512, shuffle=True, num_workers=0)
te_loader = DataLoader(TensorDataset(torch.from_numpy(X_te), torch.from_numpy(y_te)),
                        batch_size=512, shuffle=False, num_workers=0)

def metrics_orig(metrics_sc):
    return {tn: {'RMSE': v['RMSE']*y_std[TARGET_NAMES.index(tn)],
                  'MAE':  v['MAE']*y_std[TARGET_NAMES.index(tn)],
                  'R2':   v['R2']}
            for tn, v in metrics_sc.items()}

all_results = {}

# --- sklearn baselines ---
def eval_sk(mdl, Xte, yte):
    p = mdl.predict(Xte) * y_std + y_mean
    t = yte * y_std + y_mean
    res = {}
    for i,tn in enumerate(TARGET_NAMES):
        pt=p[:,:,i].flatten(); yt=t[:,:,i].flatten()
        rmse=np.sqrt(np.mean((pt-yt)**2)); mae=np.mean(np.abs(pt-yt))
        r2=1-np.sum((yt-pt)**2)/(np.sum((yt-yt.mean())**2)+1e-8)
        res[tn]={'RMSE':float(rmse),'MAE':float(mae),'R2':float(r2)}
    return res

print("Fitting sklearn baselines...")
for Cls in [PersistenceBaseline, RidgeBaseline]:
    m = Cls(); m.fit(X_tr, y_tr)
    all_results[m.name] = eval_sk(m, X_te, y_te)
    print(f"  {m.name}: NH4={all_results[m.name]['NH4_out']['RMSE']:.4f}")

lgbm = LightGBMBaseline(n_estimators=150, seed=SEED)
lgbm.fit(X_tr, y_tr)
all_results['LightGBM'] = eval_sk(lgbm, X_te, y_te)
print(f"  LightGBM: NH4={all_results['LightGBM']['NH4_out']['RMSE']:.4f}")

# --- NN training helper ---
def train_eval_nn(model, n_ep=25, lr=1e-3, name=''):
    opt  = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    sch  = torch.optim.lr_scheduler.CosineAnnealingLR(opt, n_ep)
    crit = nn.MSELoss()
    t0   = time.time()
    for ep in range(n_ep):
        model.train()
        for xb,yb in tr_loader:
            out = model(xb)
            pred = out['pred'] if isinstance(out,dict) else out
            loss = crit(pred, yb)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),1.); opt.step()
        sch.step()
    elapsed = time.time()-t0
    model.eval()
    ps, ts = [],[]
    with torch.no_grad():
        for xb,yb in te_loader:
            out=model(xb)
            p = out['pred'] if isinstance(out,dict) else out
            ps.append(p.numpy()); ts.append(yb.numpy())
    ps=np.concatenate(ps); ts=np.concatenate(ts)
    po=ps*y_std+y_mean; to=ts*y_std+y_mean
    res={}
    for i,tn in enumerate(TARGET_NAMES):
        pt=po[:,:,i].flatten(); yt=to[:,:,i].flatten()
        res[tn]={'RMSE':float(np.sqrt(np.mean((pt-yt)**2))),
                  'MAE':float(np.mean(np.abs(pt-yt))),
                  'R2':float(1-np.sum((yt-pt)**2)/(np.sum((yt-yt.mean())**2)+1e-8))}
    np_= sum(p.numel() for p in model.parameters())
    print(f"  {name}: NH4={res['NH4_out']['RMSE']:.4f} N2O={res['N2O_gN_m3']['RMSE']:.6f} params={np_:,d} t={elapsed:.0f}s")
    return res, np_, elapsed

print("\nTraining NN baselines...")
gru=GRUBaseline(input_size=N_IN,n_targets=N_TASKS,horizon=HORIZON)
all_results['GRU'],_,_ = train_eval_nn(gru, 20, name='GRU')
attm=AttMMoE(input_size=N_IN,n_tasks=N_TASKS,horizon=HORIZON)
all_results['AttMMoE'],_,_ = train_eval_nn(attm, 25, name='AttMMoE')
torch.save(attm.state_dict(), f'{OUT_DIR}/models/attmmoe_vPlantA_seed{SEED}.pt')

# --- OAKI-PL training (T040-T052) ---
print("\nTraining OAKI-PL...")
mask_80 = np.load(f'{DATA_DIR}/masks/mask_ghg_080_seed456.npy')

def train_oaki(mask_ratio_str, n_ep=25, name='OAKI-PL'):
    oaki = OAKI_PL(input_size=N_IN, n_tasks=N_TASKS, horizon=HORIZON, n_experts=6, d_model=64)
    loss_fn = PartialLabelLoss(use_dynamic_weights=True)
    opt = torch.optim.Adam(list(oaki.parameters())+list(loss_fn.parameters()), lr=1e-3)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, n_ep)
    if mask_ratio_str:
        ratio_int = int(mask_ratio_str.replace('%',''))
        mask = np.load(f'{DATA_DIR}/masks/mask_ghg_{ratio_int:03d}_seed456.npy')
    else:
        mask = None
    t0 = time.time()
    for ep in range(n_ep):
        train_epoch(oaki, tr_loader, opt, loss_fn, 'cpu',
                    mask[:len(X_tr)] if mask is not None else None, ep)
        sch.step()
    elapsed = time.time()-t0
    m = evaluate(oaki, te_loader)
    mo = metrics_orig(m)
    np_ = oaki.get_n_params()
    print(f"  {name}: NH4={mo['NH4_out']['RMSE']:.4f} N2O={mo['N2O_gN_m3']['RMSE']:.6f} params={np_:,d} t={elapsed:.0f}s")
    return mo, oaki

oaki_80, oaki_model = train_oaki('80%', 25, 'OAKI-PL (80% GHG masked)')
all_results['OAKI-PL (80% GHG masked)'] = oaki_80
torch.save(oaki_model.state_dict(), f'{OUT_DIR}/models/oaki_pl_vPlantA_seed{SEED}.pt')

oaki_full, _ = train_oaki(None, 25, 'OAKI-PL (full labels)')
all_results['OAKI-PL (full labels)'] = oaki_full

# Ablations: varying mask ratio (T041 ablation)
print("\nAblation: varying GHG mask ratio...")
for ratio in ['20%','60%','95%']:
    r,_ = train_oaki(ratio, 20, f'OAKI-PL ({ratio} GHG masked)')
    all_results[f'OAKI-PL ({ratio} GHG masked)'] = r

# Save
with open(f'{OUT_DIR}/tables/model_comparison_VPlantA_v1.json','w') as f:
    json.dump(all_results, f, indent=2)

print("\n" + "="*90)
print(f"{'Model':<40} {'NH4_RMSE':>9} {'TN_RMSE':>9} {'N2O_RMSE':>12} {'N2O_R2':>8} {'GHG_RMSE':>12}")
print("-"*90)
for mn,mr in all_results.items():
    if 'NH4_out' not in mr: continue
    print(f"{mn:<40} {mr['NH4_out']['RMSE']:>9.4f} {mr['TN_out']['RMSE']:>9.4f} "
          f"{mr['N2O_gN_m3']['RMSE']:>12.6f} {mr['N2O_gN_m3']['R2']:>8.4f} "
          f"{mr['GHG_total_kgCO2eq_m3']['RMSE']:>12.6f}")
print("="*90)
print("\n[仿真-Python-AAO] All results on synthetic data. NOT real GHG validation.")
