"""
T035-T039: Baseline Models
Persistence, Linear/Ridge/GAM, ExtraTrees/LightGBM, GRU/TCN, AttMMoE
All models trained on [仿真-Python-AAO] data
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.multioutput import MultiOutputRegressor
import lightgbm as lgb
import torch
import torch.nn as nn
from typing import Dict, Tuple, Optional, List
import warnings
warnings.filterwarnings('ignore')

TARGET_NAMES = ['NH4_out','TN_out','TP_out','E_kWh_m3','N2O_gN_m3','GHG_total_kgCO2eq_m3']

# ─── T035: Persistence Baseline ───────────────────────────────────────────────
class PersistenceBaseline:
    """Last-value persistence baseline"""
    name = 'Persistence'
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """X: (N, lookback, features), last 6 features are targets"""
        # Use last timestep targets (assumed to be last 6 cols of input)
        last = X[:, -1, -6:]  # (N, 6)
        return np.stack([last]*4, axis=1)  # (N, 4, 6)
    
    def fit(self, X_train, y_train): pass  # no training


class SeasonalPersistenceBaseline:
    """Same-day-of-week persistence"""
    name = 'SeasonalPersistence'
    
    def fit(self, X_train, y_train): 
        self.y_seasonal = y_train.mean(0, keepdims=True)
    
    def predict(self, X):
        N = len(X)
        return np.tile(self.y_seasonal, (N,1,1))


# ─── T036: Linear / Ridge Baseline ───────────────────────────────────────────
class RidgeBaseline:
    """Ridge regression with flattened window features"""
    name = 'Ridge'
    
    def __init__(self, alpha=1.0):
        self.models = [Ridge(alpha=alpha) for _ in range(6)]
        self.horizon = 4
    
    def fit(self, X_train: np.ndarray, y_train: np.ndarray):
        """X_train: (N, L, F), y_train: (N, H, 6)"""
        N, L, F = X_train.shape
        Xf = X_train.reshape(N, -1)
        for t, mdl in enumerate(self.models):
            yt = y_train[:, :, t].mean(1)  # mean over horizon
            mdl.fit(Xf, yt)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        N, L, F = X.shape
        Xf = X.reshape(N, -1)
        preds = np.stack([m.predict(Xf) for m in self.models], axis=1)  # (N, 6)
        return np.stack([preds]*self.horizon, axis=1)  # (N, 4, 6)


# ─── T037: Tree Model Baseline ───────────────────────────────────────────────
class LightGBMBaseline:
    """LightGBM multi-output regression"""
    name = 'LightGBM'
    
    def __init__(self, n_estimators=200, num_leaves=31, seed=42):
        self.params = dict(n_estimators=n_estimators, num_leaves=num_leaves,
                           random_state=seed, verbose=-1, n_jobs=-1)
        self.models = []
        self.horizon = 4
    
    def fit(self, X_train: np.ndarray, y_train: np.ndarray):
        N, L, F = X_train.shape
        Xf = X_train.reshape(N, -1)
        self.models = []
        for t in range(y_train.shape[2]):
            yt = y_train[:, :, t].mean(1)
            m = lgb.LGBMRegressor(**self.params)
            m.fit(Xf, yt)
            self.models.append(m)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        Xf = X.reshape(len(X), -1)
        preds = np.stack([m.predict(Xf) for m in self.models], axis=1)
        return np.stack([preds]*self.horizon, axis=1)


class ExtraTreesBaseline(LightGBMBaseline):
    name = 'ExtraTrees'
    def __init__(self, n_estimators=200, seed=42):
        from sklearn.ensemble import ExtraTreesRegressor
        self.params = dict(n_estimators=n_estimators, random_state=seed, n_jobs=-1)
        self.ModelClass = ExtraTreesRegressor
        self.models = []
        self.horizon = 4
    
    def fit(self, X_train, y_train):
        from sklearn.ensemble import ExtraTreesRegressor
        N, L, F = X_train.shape
        Xf = X_train.reshape(N, -1)
        self.models = []
        for t in range(y_train.shape[2]):
            yt = y_train[:, :, t].mean(1)
            m = ExtraTreesRegressor(**self.params)
            m.fit(Xf, yt)
            self.models.append(m)


# ─── T038: GRU Baseline ──────────────────────────────────────────────────────
class GRUBaseline(nn.Module):
    """Single-task GRU for multi-output prediction"""
    name = 'GRU'
    
    def __init__(self, input_size=16, hidden_size=64, n_layers=2,
                 n_targets=6, horizon=4, dropout=0.1):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden_size, n_layers, 
                          batch_first=True, dropout=dropout if n_layers>1 else 0.)
        self.head = nn.Linear(hidden_size, n_targets * horizon)
        self.n_targets = n_targets
        self.horizon = horizon
    
    def forward(self, x):
        out, _ = self.gru(x)
        last = out[:, -1, :]
        pred = self.head(last).view(-1, self.horizon, self.n_targets)
        return pred


class TCNBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size, dilation):
        super().__init__()
        pad = (kernel_size-1)*dilation
        self.conv = nn.Sequential(
            nn.utils.weight_norm(nn.Conv1d(in_ch, out_ch, kernel_size, 
                                           padding=pad, dilation=dilation)),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.utils.weight_norm(nn.Conv1d(out_ch, out_ch, kernel_size, 
                                           padding=pad, dilation=dilation)),
            nn.ReLU(),
        )
        self.downsample = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else None
        self.relu = nn.ReLU()
        self.pad = pad
    
    def forward(self, x):
        res = x if self.downsample is None else self.downsample(x)
        out = self.conv(x)[:, :, :x.size(2)]  # trim causal padding
        return self.relu(out + res)


class TCNBaseline(nn.Module):
    name = 'TCN'
    def __init__(self, input_size=16, n_channels=64, n_targets=6, horizon=4):
        super().__init__()
        self.blocks = nn.Sequential(
            TCNBlock(input_size, n_channels, 3, 1),
            TCNBlock(n_channels, n_channels, 3, 2),
            TCNBlock(n_channels, n_channels, 3, 4),
        )
        self.head = nn.Linear(n_channels, n_targets * horizon)
        self.n_targets = n_targets; self.horizon = horizon
    
    def forward(self, x):
        # x: (B, L, F) → (B, F, L)
        out = self.blocks(x.permute(0,2,1))
        last = out[:, :, -1]
        return self.head(last).view(-1, self.horizon, self.n_targets)


# ─── T039: AttMMoE (Sun et al. 2026 reproduction) ────────────────────────────
class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True)
        self.norm = nn.LayerNorm(d_model)
    
    def forward(self, x):
        attn_out, _ = self.attn(x, x, x)
        return self.norm(x + attn_out)


class Expert(nn.Module):
    def __init__(self, d_in, d_out):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, d_out*2), nn.ReLU(),
            nn.Linear(d_out*2, d_out), nn.ReLU()
        )
    def forward(self, x): return self.net(x)


class AttMMoE(nn.Module):
    """
    Attention + Mixture of Experts (AttMMoE)
    Approximate reproduction of Sun et al. 2026 architecture
    [仿真-Python-AAO] used for training
    """
    name = 'AttMMoE'
    
    def __init__(self, input_size=16, seq_len=16, d_model=64, n_heads=4,
                 n_experts=4, n_tasks=6, horizon=4):
        super().__init__()
        self.n_tasks = n_tasks; self.horizon = horizon
        
        # Temporal encoding
        self.input_proj = nn.Linear(input_size, d_model)
        self.attn = MultiHeadAttention(d_model, n_heads)
        self.pool = nn.AdaptiveAvgPool1d(1)
        
        # MMoE
        self.experts = nn.ModuleList([Expert(d_model, d_model) for _ in range(n_experts)])
        # Per-task gates
        self.gates = nn.ModuleList([
            nn.Sequential(nn.Linear(d_model, n_experts), nn.Softmax(dim=-1))
            for _ in range(n_tasks)
        ])
        
        # Per-task output heads
        self.heads = nn.ModuleList([
            nn.Linear(d_model, horizon) for _ in range(n_tasks)
        ])
        
        self._n_experts = n_experts
    
    def forward(self, x):
        """x: (B, L, F)"""
        B = x.size(0)
        
        # Attention encoding
        h = self.input_proj(x)                          # (B, L, d)
        h = self.attn(h)                                 # (B, L, d)
        h = self.pool(h.permute(0,2,1)).squeeze(-1)     # (B, d)
        
        # Expert outputs
        expert_outs = torch.stack([e(h) for e in self.experts], dim=1)  # (B, E, d)
        
        # Task-specific gating + prediction
        preds = []
        for t in range(self.n_tasks):
            g = self.gates[t](h).unsqueeze(-1)        # (B, E, 1)
            task_h = (expert_outs * g).sum(1)          # (B, d)
            pred_t = self.heads[t](task_h)             # (B, H)
            preds.append(pred_t)
        
        out = torch.stack(preds, dim=-1)  # (B, H, n_tasks)
        return out
    
    def get_gate_weights(self, x):
        """Return gate weights for interpretability"""
        B = x.size(0)
        h = self.input_proj(x)
        h = self.attn(h)
        h = self.pool(h.permute(0,2,1)).squeeze(-1)
        gates = torch.stack([g(h) for g in self.gates], dim=1)  # (B, T, E)
        return gates.detach().cpu().numpy()
