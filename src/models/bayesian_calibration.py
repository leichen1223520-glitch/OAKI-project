"""
贝叶斯参数率定模块 — PyMC v5 NUTS-MCMC 实现

采用对数正态观测模型（月度碳排放严格为正，CV约10%–25%）：
  log(y_m) = log(ŷ_m(θ, x_m)) + ε_m,  ε_m ~ N(0, σ²)

预测模型涵盖三范围排放：
  ŷ_m = Scope1(CH₄+N₂O) + Scope2(电力) + Scope3(药剂+污泥，简化项)

先验分布：第四章表4-4中的15个可率定参数（含EF_disposal）

收敛诊断：R̂ < 1.01 且有效样本量 > 400（Brooks & Gelman, 1998）

用法示例：
    from src.models.bayesian_calibration import calibrate_fpcm, load_posterior_params
    from src.models.inputs import ModelInput

    # 构建月度输入和观测
    monthly_inputs = [ModelInput(...) for _ in range(12)]
    obs = np.array([E_CO2eq_month_1, ..., E_CO2eq_month_12])

    idata = calibrate_fpcm(obs, monthly_inputs, n_samples=2000, n_chains=4)
    params = load_posterior_params(idata)

    # 用后验参数重新运行 FPCM
    from src.models.fpcm import FPCM
    result = FPCM(params).run(monthly_inputs[0])
"""
from __future__ import annotations

import numpy as np
import warnings
from typing import Sequence, Optional

from .params import ModelParams
from .inputs import ModelInput
from .fpcm import FPCM


def _fpcm_predict(params: ModelParams, monthly_inputs: Sequence[ModelInput]) -> np.ndarray:
    """
    用给定参数对所有月份的 FPCM 进行预测（仅用于非 PyMC 上下文的前向运算）。

    Returns
    -------
    predictions : np.ndarray, shape (M,)
        月度全厂碳排放 (kgCO₂eq/月)
    """
    model = FPCM(params)
    preds = []
    for inp in monthly_inputs:
        out = model.run(inp, validate=False)
        preds.append(out.E_total_CO2eq / 12.0)  # 年排放 / 12 ≈ 月排放
    return np.array(preds)


def calibrate_fpcm(
    monthly_observations: np.ndarray,
    monthly_inputs: Sequence[ModelInput],
    n_samples: int = 2000,
    n_tune: int = 1000,
    n_chains: int = 4,
    target_accept: float = 0.9,
    random_seed: int = 42,
) -> "arviz.InferenceData":
    """
    FPCM 贝叶斯参数率定（NUTS-MCMC，PyMC v5）

    Parameters
    ----------
    monthly_observations : array-like, shape (M,)
        M 个月的实测全厂碳排放 (kgCO₂eq/月)
    monthly_inputs : list of ModelInput, length M
        对应月份的 L-Core 输入数据
    n_samples : int
        每链采样数（默认 2000）
    n_tune : int
        调试步数（默认 1000）
    n_chains : int
        并行链数（默认 4）
    target_accept : float
        HMC 目标接受率（默认 0.9，提高以减少发散）
    random_seed : int
        随机种子

    Returns
    -------
    idata : arviz.InferenceData
        后验采样结果，含诊断统计量（R̂、ESS 等）
    """
    try:
        import pymc as pm
        import pytensor.tensor as pt
        import arviz as az
    except ImportError as e:
        raise ImportError(
            "贝叶斯率定需要安装 PyMC v5 及 ArviZ。\n"
            "请运行：pip install pymc>=5.0 arviz\n"
            f"原始错误：{e}"
        )

    obs = np.array(monthly_observations, dtype=float)
    M = len(obs)
    if M < 6:
        warnings.warn("观测数据少于6个月，贝叶斯率定参数辨识性可能不足。")

    with pm.Model() as model:
        # ── M1：CH₄ 先验 ─────────────────────────────────────
        MCF      = pm.LogNormal("MCF",      mu=np.log(0.028), sigma=0.60)
        B0       = pm.Normal("B0",          mu=0.60,   sigma=0.05,
                              lower=0.45, upper=0.75)
        f_boc    = pm.Normal("f_boc",       mu=0.48,   sigma=0.07,
                              lower=0.35, upper=0.65)
        theta_T  = pm.Normal("theta_T",     mu=1.040,  sigma=0.012,
                              lower=1.015, upper=1.065)

        # ── M2-nit 先验 ───────────────────────────────────────
        EF_nit   = pm.LogNormal("EF_nit",   mu=np.log(0.0035), sigma=0.65)
        DO_opt   = pm.Normal("DO_opt",      mu=2.0,    sigma=0.3,
                              lower=1.0, upper=3.0)
        f_max    = pm.LogNormal("f_max",    mu=np.log(3.0),    sigma=0.40)

        # ── M2-denit 先验 ─────────────────────────────────────
        EF_denit_ref = pm.LogNormal("EF_denit_ref",
                                    mu=np.log(0.0012), sigma=0.55)
        CN_crit  = pm.Normal("CN_crit",     mu=6.5,    sigma=1.5,
                              lower=3.5, upper=10.0)
        k_g      = pm.Normal("k_g",         mu=2.0,    sigma=0.6,
                              lower=0.5, upper=4.0)

        # ── 能耗/电网先验 ─────────────────────────────────────
        EF_grid  = pm.Normal("EF_grid",     mu=0.5839, sigma=0.03)
        r_aer    = pm.Normal("r_aer",       mu=0.576,  sigma=0.062,
                              lower=0.50, upper=0.65)

        # ── 污泥先验（Y_obs 用 Beta 分布）────────────────────
        Y_obs    = pm.Beta("Y_obs",         alpha=7.0, beta=10.0)

        # ── 污泥处置排放因子（kgCO₂eq/tDS）────────────────────
        # 先验均值 360（好氧堆肥封闭），范围 100-950 kgCO₂eq/tDS
        EF_disposal = pm.Normal("EF_disposal", mu=360.0, sigma=80.0,
                                 lower=80.0, upper=1000.0)

        # ── 残差超先验 ────────────────────────────────────────
        sigma    = pm.HalfNormal("sigma",   sigma=0.2)

        # ── 构建先验参数字典并循环计算预测值 ──────────────────
        # 注意：PyMC 张量无法直接传给 Python dataclass，
        # 这里采用"确定性节点 + pytensor 计算"模式，
        # 将模型方程显式写为 pt 表达式（仅主要项）。

        preds = []
        for inp in monthly_inputs:
            q = float(inp.Q_in)
            cod_in = float(inp.COD_in)
            tn_in = float(inp.TN_in)
            nh3n_in = float(inp.NH3N_in)
            nh3n_out = float(inp.NH3N_out)
            tn_out = float(inp.TN_out)
            t_w = float(inp.T_water)
            e_mon = float(inp.E_total_monthly)

            # M1：CH₄ 排放（kgCO₂eq/月）
            TOW = q * f_boc * cod_in * 365 * 1e-6  # tBOD/年（常数部分）
            f_sludge_org = 0.25  # 固定为先验均值（简化，防止不可辨识）
            TOW_avail = TOW * (1.0 - f_sludge_org)
            f_T = theta_T ** (t_w - 20.0)
            e_ch4_kg_annual = TOW_avail * 1000.0 * MCF * B0 * f_T
            e_ch4_co2eq = e_ch4_kg_annual * 28.0 / 12.0  # 月值

            # M2：N₂O 排放（kgCO₂eq/月）
            dN_nit = max(0.0, nh3n_in - nh3n_out) * q * 365 * 1e-3
            f_DO = 1.0  # L-Core 默认无 DO
            if inp.DO_aer is not None:
                DO = float(inp.DO_aer)
                DO_opt_val = 2.0  # 用先验均值近似
                if DO <= DO_opt_val:
                    delta = DO_opt_val - DO
                    f_DO = 1.0 + (3.0 - 1.0) * delta / (0.8 + delta)
                else:
                    delta = DO - DO_opt_val
                    f_DO = 1.0 - 0.3 * delta / (1.5 + delta)
                f_DO = max(0.0, f_DO)
            e_n2o_nit = dN_nit * EF_nit * f_DO * 1.20 * (44.0 / 28.0)

            dN_removed = max(0.0, tn_in - tn_out) * q * 365 * 1e-3
            dN_denit = dN_removed * 0.85
            COD_TN = cod_in / max(tn_in, 1e-6)
            exp_arg = -(COD_TN - CN_crit) / 1.5
            exp_arg_clipped = pt.clip(exp_arg, -10.0, 10.0)
            g_cn = EF_denit_ref * (1.0 + k_g * pt.exp(exp_arg_clipped))
            e_n2o_denit = dN_denit * g_cn * 1.20 * (44.0 / 28.0)

            e_n2o_co2eq = (e_n2o_nit + e_n2o_denit) * 265.0 / 12.0

            # Scope 2：电力
            e_scope2 = e_mon * EF_grid  # kgCO₂eq/月

            # Scope 3 简化项（药剂 + 污泥处置）
            # 药剂排放：使用台账数据（固定值，不参与率定）
            if inp.PAC_monthly is not None:
                e_pac = float(inp.PAC_monthly) * 12.0 * 1.60 / 12.0   # kgCO₂eq/月
            else:
                e_pac = 0.0
            if inp.carbon_dose_monthly is not None:
                e_carb = float(inp.carbon_dose_monthly) * 12.0 * 0.90 / 12.0
            else:
                e_carb = 0.0

            # 污泥处置：年干污泥量由Y_obs估算，EF_disposal参与率定
            # W_DS_month (tDS/月) = Y_obs × BOD_removed × Q / 1e6
            BOD_removed_mg = max(0.0, cod_in - float(inp.COD_out)) * float(inp.E_total_monthly / max(inp.E_total_monthly, 1))
            # 简化：月度干污泥 ≈ Y_obs × ΔBODmonth × Q × 30 × 1e-6
            delta_BOD_month = max(0.0, float(inp.COD_in) - float(inp.COD_out)) * 0.48
            W_DS_month = Y_obs * delta_BOD_month * q * 30 * 1e-6  # tDS/月
            e_sludge = W_DS_month * EF_disposal                    # kgCO₂eq/月

            e_scope3 = e_pac + e_carb + e_sludge

            # 月度总排放（三范围完整）
            e_total_month = e_ch4_co2eq + e_n2o_co2eq + e_scope2 + e_scope3
            preds.append(e_total_month)

        mu_pred = pt.stack(preds)

        # ── 似然函数（对数正态）───────────────────────────────
        log_mu = pt.log(pt.abs_(mu_pred) + 1e-9)
        pm.Normal("obs", mu=log_mu, sigma=sigma, observed=np.log(obs + 1e-9))

        # ── NUTS 采样 ─────────────────────────────────────────
        idata = pm.sample(
            draws=n_samples,
            tune=n_tune,
            chains=n_chains,
            target_accept=target_accept,
            random_seed=random_seed,
            progressbar=True,
            return_inferencedata=True,
        )

    return idata


def diagnose(idata: "arviz.InferenceData") -> dict:
    """
    快速收敛诊断。

    Returns
    -------
    dict with:
        r_hat_max : float   最大 R̂（< 1.05 为收敛）
        ess_min   : float   最小有效样本量（> 400 为充足）
        divergences : int   发散数量（应为 0）
        pass      : bool    是否通过所有诊断标准
    """
    try:
        import arviz as az
    except ImportError:
        return {"error": "需要安装 arviz"}

    summary = az.summary(idata, var_names=[
        "MCF", "B0", "f_boc", "theta_T",
        "EF_nit", "DO_opt", "f_max",
        "EF_denit_ref", "CN_crit", "k_g",
        "EF_grid", "r_aer", "Y_obs", "EF_disposal", "sigma",
    ])
    r_hat_max = float(summary["r_hat"].max())
    ess_min = float(summary["ess_bulk"].min())

    n_div = int(idata.sample_stats["diverging"].sum())

    # 收敛标准：R̂ < 1.01（Brooks & Gelman, 1998），ESS > 400（Gelman等, 2013）
    passed = r_hat_max < 1.01 and ess_min > 400 and n_div == 0
    return {
        "r_hat_max": r_hat_max,
        "ess_min": ess_min,
        "divergences": n_div,
        "pass": passed,
    }


def load_posterior_params(
    idata: "arviz.InferenceData",
    use_mean: bool = True,
) -> ModelParams:
    """
    从 ArviZ InferenceData 提取后验参数，返回 ModelParams。

    Parameters
    ----------
    idata : arviz.InferenceData
    use_mean : bool
        True → 使用后验均值；False → 随机抽取一组后验样本

    Returns
    -------
    ModelParams
    """
    post = idata.posterior

    def _get(name: str) -> float:
        arr = post[name].values.flatten()
        if use_mean:
            return float(np.mean(arr))
        else:
            return float(np.random.choice(arr))

    return ModelParams(
        MCF=_get("MCF"),
        B0=_get("B0"),
        f_boc=_get("f_boc"),
        theta_T=_get("theta_T"),
        EF_nit=_get("EF_nit"),
        DO_opt=_get("DO_opt"),
        f_max=_get("f_max"),
        EF_denit_ref=_get("EF_denit_ref"),
        CN_crit=_get("CN_crit"),
        k_g=_get("k_g"),
        EF_grid=_get("EF_grid"),
        r_aer=_get("r_aer"),
        Y_obs=_get("Y_obs"),
        EF_disposal=_get("EF_disposal"),
    )
