"""
validators.py — 模型输入参数合理性校验

提供 validate_model_input() 函数，对 ModelInput 数据进行范围检查，
返回 ValidationResult（含 is_valid 标志和警告列表）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


# ─── 参数合理范围（工程经验值）─────────────────────────────────────────────

_RANGES: dict[str, Tuple[float, float, str]] = {
    # (min, max, unit)
    "Q_in":             (100.0,   2_000_000.0,  "m³/d"),
    "E_total_monthly":  (1_000.0, 50_000_000.0, "kWh/月"),
    "COD_in":           (50.0,    1_200.0,       "mg/L"),
    "TN_in":            (5.0,     120.0,         "mg/L"),
    "NH3N_in":          (1.0,     100.0,         "mg/L"),
    "NH3N_out":         (0.0,     30.0,          "mg/L"),
    "TP_in":            (0.5,     30.0,          "mg/L"),
    "COD_out":          (5.0,     150.0,         "mg/L"),
    "TN_out":           (0.5,     50.0,          "mg/L"),
    "T_water":          (1.0,     35.0,          "°C"),
    "DO_aer":           (0.1,     8.0,           "mg/L"),
    "MLSS":             (1000.0,  15000.0,       "mg/L"),
    "SRT":              (3.0,     30.0,          "d"),
}

# 衍生约束
_CONSTRAINTS = [
    # (condition_fn, error_msg)
    (lambda i: i.NH3N_in >= i.NH3N_out,
     "NH3N_in 应 ≥ NH3N_out（进水氨氮应高于出水）"),
    (lambda i: i.COD_in >= i.COD_out,
     "COD_in 应 ≥ COD_out（进水COD应高于出水）"),
    (lambda i: i.TN_in >= i.TN_out,
     "TN_in 应 ≥ TN_out（进水TN应高于出水）"),
    (lambda i: i.NH3N_in <= i.TN_in,
     "NH3N_in 应 ≤ TN_in（氨氮不超过总氮）"),
]


def validate_model_input(inp) -> ValidationResult:
    """
    校验 ModelInput 实例的合理性。

    Parameters
    ----------
    inp : ModelInput
        FPCM 模型输入实例。

    Returns
    -------
    ValidationResult
        is_valid=False 表示存在严重错误；warnings 为非致命提示。
    """
    result = ValidationResult()

    # 范围检查
    for field_name, (lo, hi, unit) in _RANGES.items():
        val = getattr(inp, field_name, None)
        if val is None:
            continue  # 可选字段，跳过
        if not (lo <= val <= hi):
            severity = "error" if field_name in ("Q_in", "E_total_monthly",
                                                   "COD_in", "TN_in") else "warning"
            msg = (f"{field_name}={val:.2f} {unit} 超出合理范围 "
                   f"[{lo}, {hi}]")
            if severity == "error":
                result.add_error(msg)
            else:
                result.add_warning(msg)

    # 衍生约束
    for cond_fn, msg in _CONSTRAINTS:
        try:
            if not cond_fn(inp):
                result.add_error(msg)
        except Exception:
            pass  # 字段为 None 时跳过

    # 进水COD/TN比值（影响N₂O估算）
    if inp.TN_in and inp.TN_in > 0:
        cn_ratio = inp.COD_in / inp.TN_in
        if cn_ratio < 3.0:
            result.add_warning(
                f"进水COD/TN={cn_ratio:.2f}，低于3.0，"
                "反硝化碳源可能不足，N₂O估算偏差可能较大"
            )
        elif cn_ratio > 15.0:
            result.add_warning(
                f"进水COD/TN={cn_ratio:.2f}，偏高（>15），"
                "请确认数据质量"
            )

    # 极端水温警告
    if inp.T_water < 8.0:
        result.add_warning(
            f"水温={inp.T_water}°C，低于8°C，"
            "硝化活性受抑，N₂O和CH₄模型精度可能下降"
        )
    if inp.T_water > 30.0:
        result.add_warning(
            f"水温={inp.T_water}°C，超过30°C（训练数据范围），"
            "模型外推，建议谨慎使用结果"
        )

    return result


def validate_batch(inputs: list) -> List[ValidationResult]:
    """批量校验，返回每个输入对应的 ValidationResult 列表"""
    return [validate_model_input(inp) for inp in inputs]
