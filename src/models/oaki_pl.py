"""
T040-T052: OAKI-PL
Partial Label Multi-task Learning for AAO WWTP GHG prediction
[仿真-Python-AAO] data

Key components:
- Multi-timescale input encoding
- Partial label masked loss (T045)
- Expert network with task-specific gating (T040)
- Dynamic task weights (T041)
- Self-supervised pretraining (T047)
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, List, Dict, Tuple

TARGET_NAMES = ['NH4_out','TN_out','TP_out','E_kWh_m3','N2O_gN_m3','GHG_total_kgCO2eq_m3']
GHG_TASK_IDX = [4, 5]   # indices of GHG tasks (N2O, GHG_total)
AUX_TASK_IDX = [0,1,2,3] # indices of auxiliary tasks (water quality + energy)


# ─── T045: Partial Label Masked Loss ─────────────────────────────────────────
class PartialLabelLoss(nn.Module):
    """
    Multi-task loss with masking for missing labels.
    When GHG label is masked (mask=False), that task is excluded from loss.
    Shared layers still update from auxiliary tasks.
    """
    def __init__(self, task_names=TARGET_NAMES, ghg_indices=GHG_TASK_IDX,
                 use_dynamic_weights=True):
        super().__init__()
        n = len(task_names)
        self.n_tasks = n
        self.ghg_idx = ghg_indices
        self.use_dynamic_weights = use_dynamic_weights
        
        if use_dynamic_weights:
            # Learnable log task weights (GradNorm-style)
            self.log_sigma = nn.Parameter(torch.zeros(n))
    
    def forward(self, pred: torch.Tensor, target: torch.Tensor,
                mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, Dict]:
        """
        pred:   (B, H, T)  — predictions
        target: (B, H, T)  — targets
        mask:   (B, H, T) bool — True=label available, False=masked
        """
        B, H, T = pred.shape
        
        task_losses = []
        for t in range(T):
            pt = pred[:, :, t]
            yt = target[:, :, t]
            
            if mask is not None:
                mt = mask[:, :, t]  # (B, H) bool
                if mt.sum() == 0:
                    task_losses.append(torch.tensor(0., device=pred.device))
                    continue
                pt = pt[mt]; yt = yt[mt]
            
            loss_t = F.mse_loss(pt, yt)
            task_losses.append(loss_t)
        
        task_losses = torch.stack(task_losses)
        
        if self.use_dynamic_weights:
            # Uncertainty-weighted multi-task loss (Kendall et al. 2018)
            weights = torch.exp(-self.log_sigma)
            weighted = (weights * task_losses + self.log_sigma).sum()
            total = weighted
        else:
            total = task_losses.sum()
        
        loss_dict = {
            'total': total.item(),
            'tasks': {TARGET_NAMES[i]: task_losses[i].item() for i in range(T)},
            'ghg_loss': sum(task_losses[i].item() for i in GHG_TASK_IDX),
            'aux_loss': sum(task_losses[i].item() for i in AUX_TASK_IDX),
        }
        if self.use_dynamic_weights:
            loss_dict['task_weights'] = torch.exp(-self.log_sigma).detach().cpu().numpy()
        
        return total, loss_dict


# ─── T046: Multi-timescale Input Encoding ────────────────────────────────────
class MultiTimescaleEncoder(nn.Module):
    """
    Encode inputs from multiple timescales:
    - High-frequency branch: full 15-min window (positions 0:L)
    - Low-frequency branch: downsampled window (daily averages)
    - Static features: time-invariant plant characteristics
    """
    def __init__(self, input_size=16, d_model=64, seq_len=16, n_heads=4):
        super().__init__()
        # High-frequency: transformer on full window
        self.hf_proj = nn.Linear(input_size, d_model)
        self.hf_attn = nn.TransformerEncoderLayer(d_model, n_heads, 
                                                   dim_feedforward=d_model*2,
                                                   batch_first=True, dropout=0.1)
        
        # Low-frequency: average pooling + linear
        self.lf_pool = nn.AvgPool1d(kernel_size=4, stride=4)  # 16→4 steps
        self.lf_proj = nn.Linear(input_size, d_model)
        self.lf_enc  = nn.GRU(d_model, d_model, batch_first=True)
        
        # Fusion
        self.fusion = nn.Sequential(
            nn.Linear(d_model * 2, d_model), nn.ReLU(), nn.LayerNorm(d_model)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, L, F) → (B, d_model)"""
        # High-frequency branch
        hf = self.hf_proj(x)
        hf = self.hf_attn(hf)
        hf = hf[:, -1, :]  # last timestep
        
        # Low-frequency branch
        lf = self.lf_pool(x.permute(0,2,1)).permute(0,2,1)  # (B, L/4, F)
        lf = self.lf_proj(lf)
        _, lf_h = self.lf_enc(lf)
        lf = lf_h[-1]  # (B, d)
        
        # Fuse
        return self.fusion(torch.cat([hf, lf], dim=-1))


# ─── T040: OAKI-PL Core Model ────────────────────────────────────────────────
class OAKI_PL(nn.Module):
    """
    OAKI-PL: Partial Label Multi-task Process State Learning
    
    Architecture:
    1. Multi-timescale encoder (T046)
    2. Shared trunk
    3. n_experts expert networks (T040)
    4. Task-specific gates (T040)  
    5. Task-specific output heads (with GHG probability head, T067)
    
    Reference paper: Sun et al. 2026 (AttMMoE backbone extended with partial label)
    This implements the OAKI-PL contributions beyond AttMMoE.
    """
    name = 'OAKI-PL'
    
    def __init__(self, input_size=16, seq_len=16, d_model=64, n_heads=4,
                 n_experts=6, n_tasks=6, horizon=4, dropout=0.1,
                 use_dynamic_weights=True, use_prob_head_for_ghg=True):
        super().__init__()
        self.n_tasks = n_tasks
        self.horizon = horizon
        self.ghg_idx = GHG_TASK_IDX
        
        # T046: Multi-timescale encoder
        self.encoder = MultiTimescaleEncoder(input_size, d_model, seq_len, n_heads)
        
        # Shared projection
        self.shared = nn.Sequential(
            nn.Linear(d_model, d_model), nn.ReLU(), nn.LayerNorm(d_model)
        )
        
        # T040: Expert networks (each expert = 2-layer MLP)
        self.n_experts = n_experts
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model, d_model*2), nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model*2, d_model), nn.GELU()
            )
            for _ in range(n_experts)
        ])
        
        # Task-specific gates
        self.gates = nn.ModuleList([
            nn.Sequential(nn.Linear(d_model, n_experts), nn.Softmax(dim=-1))
            for _ in range(n_tasks)
        ])
        
        # Task-specific output heads
        # WQ/energy tasks: point prediction
        # GHG tasks: mean + log_var (Gaussian output)
        self.point_heads = nn.ModuleList([
            nn.Linear(d_model, horizon) for _ in range(n_tasks - len(GHG_TASK_IDX))
        ])
        
        if use_prob_head_for_ghg:
            # Probabilistic heads for GHG (mean + log_std)
            self.ghg_mean_heads = nn.ModuleList([
                nn.Linear(d_model, horizon) for _ in range(len(GHG_TASK_IDX))
            ])
            self.ghg_log_std_heads = nn.ModuleList([
                nn.Sequential(nn.Linear(d_model, horizon), nn.Tanh())  # bounded log_std
                for _ in range(len(GHG_TASK_IDX))
            ])
        else:
            self.ghg_mean_heads = nn.ModuleList([
                nn.Linear(d_model, horizon) for _ in range(len(GHG_TASK_IDX))
            ])
            self.ghg_log_std_heads = None
        
        self.use_prob_ghg = use_prob_head_for_ghg
    
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Encode input to shared representation"""
        h = self.encoder(x)
        return self.shared(h)
    
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        x: (B, L, F)
        Returns: dict with 'pred' (B, H, T), optionally 'ghg_log_std' (B, H, n_ghg)
        """
        B = x.size(0)
        h = self.encode(x)  # (B, d)
        
        # Expert outputs
        expert_outs = torch.stack([e(h) for e in self.experts], dim=1)  # (B, E, d)
        
        preds = []
        gate_weights = []
        
        # Non-GHG tasks
        non_ghg_idx = [i for i in range(self.n_tasks) if i not in self.ghg_idx]
        for k, t in enumerate(non_ghg_idx):
            g = self.gates[t](h).unsqueeze(-1)    # (B, E, 1)
            task_h = (expert_outs * g).sum(1)      # (B, d)
            pred_t = self.point_heads[k](task_h)   # (B, H)
            preds.append(pred_t)
            gate_weights.append(g.squeeze(-1).detach())
        
        # GHG tasks
        ghg_log_stds = []
        for k, t in enumerate(self.ghg_idx):
            g = self.gates[t](h).unsqueeze(-1)
            task_h = (expert_outs * g).sum(1)
            mu = self.ghg_mean_heads[k](task_h)
            preds.append(mu)
            gate_weights.append(g.squeeze(-1).detach())
            if self.use_prob_ghg and self.ghg_log_std_heads is not None:
                log_std = self.ghg_log_std_heads[k](task_h)
                ghg_log_stds.append(log_std)
        
        # Reorder predictions to original task order
        # Current order: non_ghg (0,1,2,3) + ghg (4,5)
        pred = torch.stack(preds, dim=-1)  # (B, H, T)
        
        out = {'pred': pred}
        if ghg_log_stds:
            out['ghg_log_std'] = torch.stack(ghg_log_stds, dim=-1)  # (B, H, n_ghg)
        
        return out
    
    def get_gate_weights(self, x: torch.Tensor) -> np.ndarray:
        """Return gate weights for interpretability analysis (T042)"""
        h = self.encode(x)
        gates = torch.stack([g(h) for g in self.gates], dim=1)  # (B, T, E)
        return gates.detach().cpu().numpy()
    
    def get_n_params(self) -> int:
        return sum(p.numel() for p in self.parameters())


# ─── T047: Self-supervised Pre-training ──────────────────────────────────────
class MaskedAutoencoder(nn.Module):
    """
    Self-supervised pre-training using masked reconstruction.
    Trained on long-term process data WITHOUT GHG labels.
    The encoder is then transferred to OAKI-PL.
    """
    name = 'MAE-Pretrain'
    
    def __init__(self, input_size=16, d_model=64, seq_len=16, mask_ratio=0.3):
        super().__init__()
        self.encoder = MultiTimescaleEncoder(input_size, d_model, seq_len)
        self.mask_ratio = mask_ratio
        self.decoder = nn.Sequential(
            nn.Linear(d_model, d_model*2), nn.ReLU(),
            nn.Linear(d_model*2, seq_len * input_size)
        )
        self.input_size = input_size
        self.seq_len = seq_len
    
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None):
        """
        x: (B, L, F)
        Returns reconstruction loss
        """
        B, L, F = x.shape
        
        # Create mask if not provided
        if mask is None:
            n_mask = int(L * self.mask_ratio)
            mask = torch.ones(B, L, dtype=torch.bool, device=x.device)
            idx = torch.randperm(L)[:n_mask]
            mask[:, idx] = False
        
        # Mask input (zero-out masked tokens)
        x_masked = x.clone()
        x_masked[:, ~mask[0], :] = 0.  # simplified: same mask for batch
        
        # Encode
        h = self.encoder(x_masked)
        
        # Decode
        recon = self.decoder(h).view(B, L, F)
        
        # Loss only on masked tokens
        loss = F.mse_loss(recon[:, ~mask[0], :], x[:, ~mask[0], :])
        return loss, recon


# ─── Training Utilities ───────────────────────────────────────────────────────
def train_epoch(model, loader, optimizer, loss_fn, device='cpu', 
                mask_array=None, epoch=0):
    """Train one epoch with partial label masking"""
    model.train()
    total_loss = 0.; n_batches = 0
    task_losses = {}
    
    for batch_idx, (xb, yb) in enumerate(loader):
        xb, yb = xb.to(device), yb.to(device)
        
        # Get mask for this batch
        if mask_array is not None:
            start = batch_idx * xb.size(0)
            end = start + xb.size(0)
            mb = torch.tensor(mask_array[start:end], dtype=torch.bool, device=device)
        else:
            mb = None
        
        out = model(xb)
        pred = out['pred']
        
        loss, loss_dict = loss_fn(pred, yb, mb)
        
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        
        total_loss += loss.item()
        n_batches += 1
        
        for k, v in loss_dict.get('tasks', {}).items():
            task_losses[k] = task_losses.get(k, 0.) + v
    
    return total_loss / n_batches, {k: v/n_batches for k,v in task_losses.items()}


@torch.no_grad()
def evaluate(model, loader, device='cpu'):
    """Evaluate model, return per-task RMSE"""
    model.eval()
    all_preds, all_tgts = [], []
    
    for xb, yb in loader:
        xb = xb.to(device)
        out = model(xb)
        all_preds.append(out['pred'].cpu().numpy())
        all_tgts.append(yb.numpy())
    
    preds = np.concatenate(all_preds, 0)  # (N, H, T)
    tgts  = np.concatenate(all_tgts,  0)
    
    # Per-task metrics
    metrics = {}
    for t, name in enumerate(TARGET_NAMES):
        pt = preds[:,:,t].flatten()
        yt = tgts[:,:,t].flatten()
        rmse = np.sqrt(np.mean((pt-yt)**2))
        mae  = np.mean(np.abs(pt-yt))
        ss_res = np.sum((yt-pt)**2)
        ss_tot = np.sum((yt-yt.mean())**2) + 1e-8
        r2 = 1 - ss_res/ss_tot
        metrics[name] = {'RMSE': float(rmse), 'MAE': float(mae), 'R2': float(r2)}
    
    return metrics
